#!/usr/bin/env python
# -*- coding; utf-8 -*-

#--------------------------------------------------------------------------------
# Name         test
# Description  test
# Author       wangzhilei
# Date         2019/6/18
#--------------------------------------------------------------------------------
import os
import re
import sys
import time
import pathlib
import logging
import random
import struct
import argparse
import argcomplete
from binaryornot.check import is_binary

log = logging.getLogger()
g_align = 0
g_padding = 0

def input_is_binary_file(filename):
    return is_binary(filename)


def input_files_is_all_binary(in_list):
    is_bin = 1

    for item  in in_list:
        if not input_is_binary_file(item):
            is_bin = 0
            break
        else:
            log.debug("input:%s, is_binary_file:%d", item, is_bin)
            pass

    return is_bin


def log_configuration():
    log.setLevel(logging.DEBUG)

    rq = time.strftime("%Y%m%d%H%M", time.localtime(time.time()))
    log_path = os.path.dirname(os.getcwd()) + "/logs/"
    log_name = log_path + rq + ".log"
    log_file = log_name

    is_exist = os.path.exists(log_path)
    if not is_exist:
        os.makedirs(log_path)

    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] -"
                                  " %(levelname)s: %(message)s")
    fh.setFormatter(formatter)
    log.addHandler(fh)

    log.debug(rq)
    pass

def filename_derived_factor():
    time_key = time.strftime("%H%M", time.localtime(time.time()))
    random_key = "{}".format(random.randint(1, 999))

    return  '_t'+ time_key + '_r' + random_key

def convert_handler(out_file, in_file):
    log.debug("\n\nout_file and in_file is the following:")
    log.debug("%s", out_file)
    log.debug("%s, size:%d", in_file, os.path.getsize(in_file))

    if not out_file:
        out_file = 'out'

    out_hfile_name = out_file + ".h"
    out_cfile_name = out_file + ".c"

    if pathlib.Path(out_hfile_name).exists():
        log.debug("%s exist", out_hfile_name)

    if pathlib.Path(out_cfile_name).exists():
        log.debug("%s exist", out_hfile_name)

    if os.path.exists(out_hfile_name) or os.path.exists(out_cfile_name)\
            or (not out_file):
        factor = filename_derived_factor()
        out_hfile_name = re.sub(r"\W", "_", out_file).lower() + factor + '.h'
        out_cfile_name = re.sub(r"\W", "_", out_file).lower() + factor + '.c'

    log.debug("header file name:%s", out_hfile_name)
    log.debug("c file name:     %s", out_cfile_name)

    hf_handler = open(out_hfile_name, "w")
    cf_handler = open(out_cfile_name, "w")

    # header file macro#
    hf_macro = "_" + re.sub(r"\W", "_", out_file).upper() + "_H_"
    hf_handler.write("#ifndef {0}\n#define {0}\n\n".format(hf_macro))

    output_binary(in_file, hf_handler, cf_handler)

    hf_handler.write("\n#endif \n //eof \n")
    hf_handler.close()
    cf_handler.close()
    pass


def output_binary(in_file,h_file_handler, c_file_handler):
    global g_align, g_padding

    base_name = os.path.basename(in_file)
    symbol_name = re.sub(r"\W", "_", base_name)
    h_file_handler.write("extern const unsigned char {}_array[];\n".format(symbol_name))
    c_file_handler.write("\n\nconst unsigned char {}_array[] = \n".format(symbol_name))

    c_file_handler.write("{")
    in_file_handler = open(in_file, "rb")

    in_file_len = os.path.getsize(in_file)
    padding_len = 0
    padding_val = 0
    if g_align:
        padding_len = g_align - in_file_len % g_align;
        padding_val = g_padding & 0xff
        log.debug("padding length:%d", padding_len)
        log.debug("padding value:0x%2x", padding_val)
    log.debug("input file length:%d, padding length:%d, padding value:0x%02x", in_file_len, padding_len, padding_val)

    while True:
        cell = in_file_handler.read(16)

        i = 0
        if len(cell) < 16:
            c_file_handler.write("\n      ")
            for b in cell:
                if type(b) is str:
                    b = ord(b)
                c_file_handler.write("0x{:02x}, ".format(b))

                i += 1
                if (0 == (i % 8)) and (i != len(cell)):
                    c_file_handler.write("\n      ")

            if padding_len and g_align:
                for j in range(padding_len):
                    c_file_handler.write("0x{:02x}, ".format(padding_val))
                    i = i + 1

                    if (8 == i) and (i != (len(cell) + padding_len)):
                        c_file_handler.write("\n      ")

            if (len(cell) + padding_len) == i:
                c_file_handler.write("\n")
            break

        c_file_handler.write("\n      0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x},"
                             "\n      0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x},"
                             .format(*struct.unpack("BBBBBBBBBBBBBBBB", cell)))

    in_file_handler.close()
    c_file_handler.write("};\n\n//eof \n \n")
    pass

def merge_in_files(in_file, in_list):
    in_files = []

    for item in in_list:
        in_files.append(item)

    if not in_file in in_list:
        if in_file:
            in_files.append(in_file)

    print("input all files:", in_files)

    return in_files

def convert_main():
    global g_padding, g_align

    log_configuration()

    parse = argparse.ArgumentParser()

    ''' This method will get the file handler, based on opening the file with access mode.
        args.in_file = <_io.TextIOWrapper name = "xxx.bin" mode = "r" encoding='cp936'>
        parse.add_argument('in_file', type=argparse.FileType('r'),help='input binary file')
    '''

    parse.add_argument('in_file', type=str, help='input binary file')
    parse.add_argument('--output', '-o', dest="o", type=str, help="output c file name")
    parse.add_argument('--input', '-i', dest="i", type=str, nargs="*", help="input binary file name")
    parse.add_argument('--align', '-a', dest="a", type=lambda x: int(x,0), help="align number")
    parse.add_argument('--padding', '-p', dest="p", type=lambda x: int(x,0), help="padding value")
    args = parse.parse_args()

    log.debug(args)

    if not args:
        sys.exit(1)

    if not args.a:
        args.a = 0

    if args.a and (not args.p):
        args.p = 0x0

    g_align = args.a
    g_padding = args.p

    in_container = []
    if args.i:
        in_container = merge_in_files(args.in_file, args.i)

        if not input_files_is_all_binary(in_container):
            sys.exit(1)

        for in_item in in_container:
            convert_handler(args.o, in_item)
    else:
        convert_handler(args.o, args.in_file)
    pass

if __name__ == "__main__":
    convert_main()
