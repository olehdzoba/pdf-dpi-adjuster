# PDF DPI Adjuster

## Background

I developed this program to address an issue I encountered with the Windows Scan app. The app allows you to scan pictures into a PDF at different resolutions. However, when I set the resolution to 300x300 pixels per inch (ppi), the app saved the PDF with a smaller DPI of 72x72 ppi. This lower DPI caused the dimensions of the PDF to become excessively large when pixels were converted to centimeters. For example, when I scanned an A4 paper (21x29cm), the resulting PDF had dimensions of ~90x120cm. While the pixel ratio of 2480x3425 was correct for A4 paper size with a DPI of 300, the incorrect DPI setting caused Adobe Reader to display the scan as unnaturally large.

## What This Program Does

This program is designed to adjust the DPI of images within a PDF without altering the size or scaling of the images themselves.

## Usage

To get started, follow these steps:

1. Install the necessary dependencies by running the following command:

   ```
   pip install -r requirements.txt
   ```

2. For detailed usage instructions, use the `--help` option to access further guidance and options.

Feel free to utilize this program to correct DPI discrepancies in your PDFs and ensure they display at the intended dimensions.
