from contextlib import contextmanager
import multiprocessing
import os
import subprocess
import tempfile
import time
import urllib.request
import shutil
import sys
import zipfile

PYTHON_BINARY = sys.executable
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CLCACHE_SCRIPT = os.path.join(SCRIPT_DIR, "..", "clcache.py")
CLCACHE_CMD = [PYTHON_BINARY, CLCACHE_SCRIPT]

PROJECT_URL = "https://github.com/randombit/botan/archive/1.11.31.zip"
PROJECT_ZIP_FILENAME = "botan.zip"

WORKING_DIR = os.getcwd()
JOBS = multiprocessing.cpu_count()

def ensure_downloaded(url, localfile):
    """
    Download the given url and save it at localfile. If the local file already exists, do nothing.
    :param url:
    :param localfile:
    :return:
    """
    if not os.path.exists(localfile):
        tmppath = localfile + ".part"
        urllib.request.urlretrieve(url, filename=tmppath)
        os.rename(tmppath, localfile)

def extract(archive_path, root_path):
    """
    Never extract archives from untrusted sources without prior inspection using this method.
    """
    archive_path = os.path.abspath(archive_path)
    root_path = os.path.abspath(root_path)
    with cd(root_path):
        with zipfile.ZipFile(archive_path, "r") as unzip:
            root_folder = unzip.namelist()[0]
            unzip.extractall()
    return root_folder

@contextmanager
def cd(targetDirectory):
    oldDirectory = os.getcwd()
    os.chdir(os.path.expanduser(targetDirectory))
    try:
        yield
    finally:
        os.chdir(oldDirectory)

@contextmanager
def benchmark(title):
    start = time.time()
    try:
        yield
    finally:
        end = time.time()
        s = end - start
        print('Runtime {}: {}s'.format(title, round(s)))

def reset(log):
    if os.path.exists("build"):
        print("Removing build dir ...", file=log)
        shutil.rmtree("build")

    print("Configuring Botan ...", file=log)
    subprocess.check_call([
        PYTHON_BINARY,
        "configure.py",
        "--cc-bin=clcache.bat",
        "--no-autoload",
        "--enable-modules=tls,auto_rng", # add auto_rng because of bug https://github.com/randombit/botan/issues/615
    ], stdout=log)

if __name__ == '__main__':
    print("Running {} parallel jobs".format(JOBS))

    with open("log.txt", "w") as logfile:
        with tempfile.TemporaryDirectory(prefix=os.path.join(SCRIPT_DIR, "botan_")) as tmpDir, cd(tmpDir):
            ensure_downloaded(PROJECT_URL, os.path.join(WORKING_DIR, PROJECT_ZIP_FILENAME))
            root_folder_name = extract(os.path.join(WORKING_DIR, PROJECT_ZIP_FILENAME), ".")

            with cd(root_folder_name):

                #time.sleep(30)

                reset(logfile)
                with benchmark("cold cache"):
                    subprocess.check_call(["jom", "/nologo", "-j{}".format(JOBS)], stdout=logfile)

                for i in range(3):
                    number = i+1
                    reset(logfile)
                    with benchmark("hot cache " + str(number)):
                        subprocess.check_call(["jom", "/nologo", "-j{}".format(JOBS)], stdout=logfile)
