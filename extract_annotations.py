import os
import re
import fitz
import difflib

SECTION_TEXT = "## "
QUOTING_TEXT = "  > "

def merge (l, r):
    m = difflib.SequenceMatcher(None, l, r)
    for o, i1, i2, j1, j2 in m.get_opcodes():
        if o == 'equal':
            yield l[i1:i2]
        elif o == 'delete':
            yield l[i1:i2]
        elif o == 'insert':
            yield r[j1:j2]
        elif o == 'replace':
            yield l[i1:i2]
            yield r[j1:j2]

def _parse_highlight(annot, wordlist) -> str:
    points = annot.vertices
    if points is None:
        return ""
    quad_count = int(len(points) / 4)
    sentence = ""
    for i in range(quad_count):
        # where the highlighted part is
        r = fitz.Quad(points[i * 4 : i * 4 + 4]).rect
        words = [w for w in wordlist if fitz.Rect(w[:4]).intersects(r)]
        if sentence:
            merged = merge(sentence.split(), [w[4] for w in words])
            sentence = ' '.join(' '.join(x) for x in merged)
        else:
            sentence = " ".join(w[4] for w in words)
    return sentence.replace("- ","")

def extract_annotation(filename, quotes=QUOTING_TEXT, sections=SECTION_TEXT):
    annot_doc = []
    foldername = os.path.dirname(filename)

    # open the PDF in MuPDF
    doc = fitz.open(filename)
    # Get the name of the file without any extensions
    basename = os.path.basename(filename).replace(".pdf", "")
    # open the Annot_Doc file
    annot_doc.append(F"\n\n{sections}{basename}\n\n")
    # loop to flip through pages
    for page in doc:
        wordlist = page.get_text("words")
        ranNum = 1
        # Loop through the annotations
        for annot in page.annots(): # take only the annotations that are comments or highlights
            # Data that might be useful
            if annot.type[0] in (0, 8): 
                text = _parse_highlight(annot, wordlist)
                comment_text = annot.info["content"]
                if text:
                    annot_doc.append(f"{quotes}{text} \n")
                if comment_text:
                    annot_doc.append(f"{quotes}Comentário: {comment_text} \n")

            if annot.type[0] in (4, 5):
                zoom_x = 5.0  # horizontal zoom
                zomm_y = 5.0  # vertical zoom
                mat = fitz.Matrix(zoom_x, zomm_y)  # zoom factor 5 in each dimension

                clip = fitz.Rect(annot.rect)
                pix = page.get_pixmap(matrix=mat, clip=clip)
                pix_text = annot.info["content"]
                pix_title = pix_text.split("\r",1)[0]
                pix_title_new = ""    
                for a in pix_title:
                    if a!='#':
                        pix_title_new += a
                
                if pix_text =='':
                    pix_title_new = str(ranNum)
                    ranNum += 1
                pix_title = pix_title_new
                nameImg = "{}/Img_P{}_{}.png".format(foldername, (page.number+1), pix_title)
                pix.save(nameImg)
                annot_doc.append(f"{quotes}![[Img_P{page.number+1}_{pix_title}.png]]\n\n")

    doc.close()
    return '\n'.join(annot_doc)

def main():
    filelist = [f for f in os.listdir() if f.endswith(".pdf")]
    annotation_file = "annotations.md"
    extract_annotation(filelist, annotation_file)

if __name__ == "__main__":
    main()