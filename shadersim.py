#!/usr/bin/env python

import glob
import os
import subprocess
import re
from strsimpy.metric_lcs import MetricLCS
from colorama import just_fix_windows_console
from termcolor import colored
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool 
from subprocess import Popen, PIPE, call
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from tqdm import tqdm

# Globals
input_disasm = ""        # disasm from Razor we are going to compare our shaders against
input_linecount = 0      # line count in it
shaders = []             # array of dicts of sanitized disasm and input path for all our shaders: [{'data': "", 'path': ""}]
metric_lcs = MetricLCS() # the thing we use for similarity check
shaders_info = []        # output info of shaders similarity to input disasm

# Clear out the output of Razor / psp2shaderperf so that it doesn't include
# line numbers and any intro text
def sanitize_disasm(text):
    if "Secondary program:" in text:
        idx = text.index("Secondary program:")
        leng = len("Secondary program:")
        text = text[idx+leng:]
        text = text.replace('Primary program:', '')
        text = text.replace('Primary Program', '')
    else:
        if "Secondary Program" in text:
            idx = text.index("Secondary Program")
            leng = len("Secondary Program")
            text = text[idx+leng:]
            text = text.replace('Primary program:', '')
            text = text.replace('Primary Program', '')
        else:
            if "Primary program:" in text:
                idx = text.index("Primary program:")
                leng = len("Primary program:")
                text = text[idx+leng:]

            if "Primary Program" in text:
                idx = text.index("Primary Program")
                leng = len("Primary Program")
                text = text[idx+leng:]

    text = re.sub(r"\d+ *:", "", text)
    text = re.sub('\t', ' ', text)
    text = re.sub(' +', ' ', text)
    text = text.replace('\\r\\n', '\n')
    text = text.replace('\\n', '\n')
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\n ', '\n', text)

    while text[0] == ' ' or text[1] == '\t' or text[1] == '\n':
        text = text[1:]

    if text[-1] == "'":
        text=text[:-1]

    return text.strip()


# If `text` has more lines than `n`, trims it to the `n`-th newline
def line_limit(text, n):
    l = [i for i in range(0, len(text)) if text[i:].startswith('\n')]  
    if len(l) >= n:
        pos = l[n-1]
        return text[:pos]
    else:  
        return text


# Run psp2shaderperf for provided `gxp` path. Also checks for existing cache.
# Returns a dictionary of sanitized disasm and input path: {'data': "", 'path': ""}
def do_disasm(gxp):
    out = ""
    shader_name = Path(gxp).stem
    disasm_path = Path('./disasm/' + shader_name + '.txt')
    
    if disasm_path.exists():
        with open(disasm_path) as f:
            try:
                out = sanitize_disasm(f.read())
                return {'data': sanitize_disasm(out), 'path': gxp}
            except Exception as e:
                print(f"do_disasm: Unable to read input ({str(f)})\n")

    proc = Popen(["psp2shaderperf.exe", "-disasm", gxp], shell=True, stdout=PIPE, stderr=PIPE)
    (output, error) = proc.communicate()

    out = str(output)
    with open(disasm_path, "w") as f:
        f.write(out)

    return {'data': sanitize_disasm(out), 'path': gxp}


# Initialize worker thread that will compute similarity
def similarity_worker_initialize(local):
    local.metric_lcs = MetricLCS()


# Main function of worker thread that computes similarity.
def similarity_worker_process(inp):
    inp["data"] = line_limit(inp["data"], input_linecount)
    return {"path": inp["path"], "similarity": 1.0 / inp["local"].metric_lcs.distance(input_disasm, inp["data"])}


# Use Colorama to make Termcolor work on Windows too
just_fix_windows_console()


# Read input
with open("input.txt") as f:
    try:
        input_disasm = sanitize_disasm(f.read())
    except Exception as e:
        print(f"Unable to read input ({str(f)})\n")

input_linecount = input_disasm.count('\n')


# Prepare disasms for all our shaders, using a pool of 16 workers
disasms_to_do = []
for file in glob.glob("shaders_gxp/*.gxp"):
    disasms_to_do.append(file)

os.makedirs("disasm", exist_ok=True) # Make sure cache dir exists

print("Collecting disassembly for all shaders")

pool = ThreadPool(16)
shaders = list(tqdm(pool.map(do_disasm, disasms_to_do), total=len(disasms_to_do)))
pool.close()
pool.join()

# Calculate similarity between all our shaders and input, using a pool of 16 workers
print("\nComputing similarity between input and all shaders")
local = threading.local()
shaders = [{**item, 'local':local} for item in shaders]
with ThreadPoolExecutor(max_workers=16, initializer=similarity_worker_initialize, initargs=(local,)) as executor:
    shaders_info = list(tqdm(executor.map(similarity_worker_process, shaders), total=len(shaders)))

# Print out the results
print("\nResults:")
for s in sorted(shaders_info, key=lambda d: d['similarity'], reverse=True):
    if s['similarity'] > 100:
        print(colored("Shader " + s["path"] + " : "+ str(s["similarity"]), 'green'))
    elif s['similarity'] > 50:
        print(colored("Shader " + s["path"] + " : "+ str(s["similarity"]), 'yellow'))
    elif s['similarity'] > 0:
        print(colored("Shader " + s["path"] + " : "+ str(s["similarity"]), 'red'))
