import argparse, sys, os, shutil, tempfile, time
from datetime import datetime

from PIL import Image
import fitz
import img2pdf 

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

handled_files = []

def append_log(line, level="INFO"):
    logfile = os.path.basename(__file__, ".log")
    with open(logfile, "a") as f:
        f.write(f"{level}-{datetime.now()}: {line}")


def extract_picture(pdf_path, out_path):
    pdf_document = fitz.open(pdf_path)

    if pdf_document.page_count > 1:
        raise Exception("Unexpected number of pages in PDF: ", pdf_document.page_count)

    page = pdf_document.load_page(0)

    # !! This way of extracting image does not preserve DPI of the image and always gives 96x96ppi
    pix = page.get_pixmap()
    pix.save(out_path)

    pdf_document.close()


def change_dpi(img_path, out_path, dpi):
    img = Image.open(img_path)

    img.info["dpi"] = dpi
    
    img.save(out_path, dpi=dpi) 


def img_to_pdf(img_path, out_path):
    with open(out_path,"wb") as f:
	    f.write(img2pdf.convert(img_path))


def fix_pdf(original_pdf, dpi):
    try:
        start = time.perf_counter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Moving original file to temporary directory while it is being manipulated
            moved_pdf = f"{tmpdir}/{os.path.basename(original_pdf)}"
            shutil.move(original_pdf, moved_pdf)
            
            scan_img = f"{tmpdir}/_scan.png"
            scan_img300 = f"{tmpdir}/_scan300.png"
        
            extract_picture(moved_pdf, scan_img)
            change_dpi(scan_img, scan_img300, dpi)
            img_to_pdf(scan_img300, original_pdf)
        
            end = time.perf_counter()
            append_log(f"Fixed {original_pdf}: {round(end - start, 2)}s")

    except Exception as e:
        append_log(f"Skipped file {original_pdf} due to exception: {e}")


class Watcher(FileSystemEventHandler):
    def __init__(self, dpi):
        super().__init__()
        self.dpi = dpi

    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path in handled_files:
            handled_files.remove(event.src_path)
            return
        
        if event.src_path.endswith(".pdf"):
            # Required so that the watcher does not react to the processed file
            handled_files.append(event.src_path)

            fix_pdf(event.src_path, self.dpi)
        

def watch_folder(folder, dpi):
    event_handler = Watcher(dpi)
    observer = Observer()

    observer.schedule(event_handler, folder, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A CLI tool that sets resolution of the image within PDF to custom DPI without changing its demensions. Caution: may distort the size of the image if you process the same image twice or if you set incorrect DPI.")
    subparsers = parser.add_subparsers(title="Commands", dest="command")

    fix_parser = subparsers.add_parser("fix", help="Fix resolution of a specific file.")
    fix_parser.add_argument("filename", help="Path to the file to fix.")
    fix_parser.add_argument("-x", "--dpi", help="DPI value that you want to set for PDF image (e.g 300,300).")

    watch_parser = subparsers.add_parser("watch", help="Watch a specific directory and fix all files there.")
    watch_parser.add_argument("dirname", help="Path to the directory to watch.")
    watch_parser.add_argument("-x", "--dpi", help="DPI value that you want to set for PDF image (e.g 300,300).")

    args = parser.parse_args()
    dpi = tuple(map(int, (args.dpi if args.dpi else "300,300").split(',')))
    
    try:
        if args.command == "fix":
            fix_pdf(args.filename, dpi)
        
        if args.command == "watch":
            watch_folder(args.dirname, dpi)
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        append_log(str(e), level="ERROR")
    