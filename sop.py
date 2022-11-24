import colored
from colored import stylize
from sympy import quo
from tqdm import tqdm
import argparse
import logging
import sys
import tempfile
import shutil
from pathlib import Path
import os
import subprocess
from pdf_title import extract_title
from extract_annotations import extract_annotation

logger = logging.getLogger("sop")
handler = logging.FileHandler('sop.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s', 
                              datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class PdfTitleConfig:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def printc(text, color="white"):
    print(stylize(text, colored.fg(color)))

def main(args):

    if args.organize:
        printc("Organize Files","green")
        OrganizeFilesRecursive(args.directory)

    if args.rename:
        printc("Rename files","green")
        RenameFiles(args.directory)

    if args.annotation:
        printc("Extract Annotation files","green")
        ExtractAnnotationFiles(args.directory, args.pdf, args.html)
        
    return 0,

def OrganizeFilesRecursive(inputPath):
    files = [str(p) for p in Path(inputPath).rglob("*.pdf")]
    printc(f"Total number of files {len(files)}", "green")
    OrganizeFiles(files)

def OrganizeFiles(files):
    for num, file in enumerate(files):
        dir = os.path.dirname(file)
        filename = os.path.basename(file)
        try:
            os.rename(file, os.path.join(dir, f"{num:03d} - {filename}"))
        except Exception as e:
            logger.error(e)

def RenameFiles(inputPath):
    files = [str(p) for p in Path(inputPath).rglob("*.pdf")]
    printc(f"Total number of files {len(files)}", "green")

    for file in tqdm(files):
        logger.info(f"Processing {file}")
        
        fileTitle = GetPDFTitle(file)
        if fileTitle is None:
            logger.error(f"Extract PDF Title. Skipping file: {file}")
            continue

        try:
            if isinstance(fileTitle,list):
                fileTitle = fileTitle[0]
            fixTitle = fileTitle.encode('utf-8','ignore').decode("utf-8") # remove invalid utf8
            fixTitle = fixTitle.replace( ":", "")
            fixTitle = fixTitle[:100] # only 100 char
        except Exception as e:
            logger.error(f"Extract PDF Title. Skipping file: {file}")
            logger.error(e)
            continue

        dir = os.path.dirname(file)
        try:
            os.rename(file, os.path.join(dir, f"{fixTitle}.pdf"))
        except Exception as e:
            logger.error(e)

def ExtractAnnotationFiles(inputPath, toPDF, toHTML):
    files = [str(p) for p in Path(inputPath).rglob("*.pdf")]
    printc(f"Total number of files {len(files)}", "green")
    annotationFile = os.path.join(inputPath, "annotations.md")
    texFile = os.path.join(tempfile.gettempdir(),"annotations.tex")

    if os.path.exists(texFile):
        os.remove(texFile)
    if os.path.exists(annotationFile):
        os.remove(annotationFile)

    for file in tqdm(files):
        logger.info(f"Processing {file}")
        ExtractPDFAnnotations(file, annotationFile, toHTML)
    
    if toPDF or (toPDF == False and toHTML == False):
        PandocMD2TEX(annotationFile, texFile)
        RemoveSectionNumber(texFile)
        RunLatex(texFile, annotationFile.replace("md","pdf"))
    if toHTML:
        PandocMD2HTML(annotationFile, annotationFile.replace("md","html"))

    # os.remove(annotationFile)

def ExtractPDFAnnotations(filename, outputfilename, toHTML=False):
    try:
        if toHTML:
            annotations =  extract_annotation(filename, quotes="  - ")
        else:
            annotations =  extract_annotation(filename)
    except Exception as e:
        logger.error(e)
        return 

    with open(outputfilename, "a+", encoding="utf-8") as f:
        f.write(annotations)
        if not toHTML:
            f.write("\\newpage\n")

def PandocMD2TEX(filename, outputfilename):
    dir = str(Path(__file__).parent.resolve())
    cmd = [os.path.join(dir,"pandoc/pandoc.exe"),  
           filename, 
           "-o", outputfilename,
           '--template=minimal_template.tex'] # %appdata%/pandoc/templates
    
    subprocess.run(cmd)

def PandocMD2HTML(filename, outputfilename):
    dir = str(Path(__file__).parent.resolve())
    cmd = [os.path.join(dir,"pandoc/pandoc.exe"),
        #    '--template=github.html',
           "-s", filename, 
           "-o", outputfilename]
    
    subprocess.run(cmd)

def RunLatex(filename, outputfilename):
    cmd = ["pdflatex", 
           "-interaction=nonstopmode",
           f"-output-directory={os.path.dirname(filename)}",
            filename]
    subprocess.run(cmd)

    shutil.copyfile(filename.replace("tex","pdf"), outputfilename)

def RemoveSectionNumber(filename):
    # Read in the file
    with open(filename, 'r') as file :
        filedata = file.read()
    # Replace the target string
    filedata = filedata.replace("\\subsection", "\\subsection*")
    filedata = filedata.replace("\\section", "\\section*")
    # Write the file out again
    with open(filename, 'w') as file:
        file.write(filedata)

def GetPDFTitle(pdfFile, max_length=250, min_length=15, multiline=True, rename=False, top_margin=70):
    config = PdfTitleConfig(file=pdfFile, max_length=max_length, min_length=min_length, multiline=multiline, rename=rename, top_margin=top_margin)
    try:
        title = extract_title(pdfFile, config)
        if len(title) < 45:
            # try again 
            config = PdfTitleConfig(file=pdfFile, max_length=max_length, min_length=30, multiline=multiline, rename=rename, top_margin=100)
            title = extract_title(pdfFile, config)
            
        return title
    except Exception as e:
        logger.error(e)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rename and organize files.')

    parser.add_argument('-d','--directory', dest='directory', type=str, required=True,
                    help='Directory with pdf files')
    parser.add_argument('-o', '--organize',  action='store_true', required=False,
                    help='Organize files in directory and subdirectory. Rename all directories as follows "001 - direct_name" or Rename all articles as follows "001 - pdf_name.pdf"')
    parser.add_argument('-m', '--rename',  action='store_true', required=False,
                    help='Rename files using paper title')
    parser.add_argument('-a', '--annotation',  action='store_true', required=False,
                    help='Extract annotations')
    parser.add_argument('-pdf', '--pdf',  action='store_true', required=False,
                    help='Extract annotations to pdf')
    parser.add_argument('-html', '--html',  action='store_true', required=False,
                    help='Extract annotations to html')
    args = parser.parse_args()
    parser.exit(*main(args))
