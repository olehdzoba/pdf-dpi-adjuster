import argparse, sys, os, shutil, tempfile, time
from datetime import datetime, date

from PIL import Image
import fitz
import img2pdf 

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

recently_created = []
recently_proccessed = []

def append_log(line, level="INFO"):
    logfile = os.path.join(os.path.dirname(__file__), ".log")
    with open(logfile, "a") as f:
        f.write(f"{level}-{datetime.now()}: {line}\n")


def extract_picture(pdf_path, out_path):
    with fitz.open(pdf_path) as pdf_document:
        if pdf_document.page_count > 1:
            raise Exception("Unexpected number of pages in PDF: ", pdf_document.page_count)

        page = pdf_document.load_page(0)

        # !! This way of extracting image does not preserve DPI of the image and always gives 96x96ppi
        pix = page.get_pixmap()
        pix.save(out_path)


def change_dpi(img_path, out_path, dpi):
    with Image.open(img_path) as img:
        img.info["dpi"] = dpi
        
        img.save(out_path, dpi=dpi) 


def img_to_pdf(img_path, out_path):
    with open(out_path,"wb") as f:
	    f.write(img2pdf.convert(img_path))


def retry_move(src, dest):
    retries = 0
    while retries < 5:
        try: 
            shutil.move(src, dest)
            break
        except PermissionError:
            retries += 1
        except Exception as e: 
            raise e


def fix_pdf(original_pdf, dpi):
    try:
        start = time.perf_counter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Moving original file to temporary directory while it is being manipulated
            moved_pdf = f"{tmpdir}/{os.path.basename(original_pdf)}"
            retry_move(original_pdf, moved_pdf)
            
            scan_img = f"{tmpdir}/_scan.png"
            scan_img300 = f"{tmpdir}/_scan300.png"
        
            extract_picture(moved_pdf, scan_img)
            change_dpi(scan_img, scan_img300, dpi)
            img_to_pdf(scan_img300, original_pdf)
        
            end = time.perf_counter()
            append_log(f"Fixed {original_pdf}: {round(end - start, 2)}s")

    except Exception as e:
        append_log(f"Skipped file {original_pdf} due to exception: {e}", level="ERROR")


class CleanWatcher(FileSystemEventHandler):
    def __init__(self, dpi):
        super().__init__()
        self.dpi = dpi

    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path in recently_proccessed:
            recently_proccessed.remove(event.src_path)
            return
        
        if event.src_path.endswith(".pdf"):
            # Required so that the watcher does not react to the processed file
            recently_proccessed.append(event.src_path)

            fix_pdf(event.src_path, self.dpi)


class WindowsScanWatcher(FileSystemEventHandler):
    def __init__(self, dpi):
        super().__init__()
        self.dpi = dpi

    def on_created(self, event):
        # Window Scan works weirdly, when scanned it creates a file which ends with today's date and every next 
        # will be appended with index (e.g. (2), (3), etc.). When it appends an index it renames the file 
        # thus causing problem with this program

        if event.is_directory:
            return
        
        if event.src_path in recently_proccessed:
            recently_proccessed.remove(event.src_path)    
            return

        if event.src_path.endswith(".pdf"):
            # First file will not be renamed so we should process the file immediately
            if os.path.basename(event.src_path).replace(".pdf", "").endswith(str(date.today()).replace("-", "")):
                recently_proccessed.append(event.src_path)
                
                time.sleep(1)
                fix_pdf(event.src_path, self.dpi)
            else:
                recently_created.append(event.src_path)

        
    def on_moved(self, event):
        if event.is_directory:
            return
        
        if event.dest_path.endswith(".pdf") and event.src_path in recently_created:
            recently_proccessed.append(event.dest_path)

            time.sleep(1)
            fix_pdf(event.dest_path, self.dpi)

            recently_created.remove(event.src_path)


def watch_folder(folder, dpi, winscan=False):
    event_handler = WindowsScanWatcher(dpi) if winscan else CleanWatcher(dpi) 
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
    watch_parser.add_argument("-d", "--dpi", help="DPI value that you want to set for PDF image (e.g 300,300).")
    watch_parser.add_argument("-w", "--winscan", help="If you want to make it work for Windows Scan app.", action="store_true")

    args = parser.parse_args()
    dpi = tuple(map(int, (args.dpi if args.dpi else "300,300").split(',')))
    
    try:
        if args.command == "fix":
            fix_pdf(args.filename, dpi)
        
        if args.command == "watch":
            watch_folder(args.dirname, dpi, args.winscan)
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        append_log(str(e), level="ERROR")
    