from pathlib import Path
from html import escape
from smtplib import SMTP

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import streamlit as st


def send_email(upload_result, email_addr_receiver, added_to_community, community_name, mode):
    subject = "CS-MACH1 Zenodo uploader notification"

    email_addr_from = st.secrets.get("PROJECT_EMAIL")
    smtp_server = st.secrets.get("EMAIL_SMTP_SERVER")
    smtp_port = st.secrets.get("EMAIL_SMTP_PORT")
    password = st.secrets.get("EMAIL_PASSWORD")

    if mode == "upload_success":

        metadata = upload_result.get("metadata", {})
        links = upload_result.get("links", {})

        title = upload_result.get("title", "-")
        record_id = upload_result.get("recid", upload_result.get("id", "-"))

        doi = upload_result.get("doi", "-")

        publication_date = metadata.get("publication_date", "-")

        community = "-"
        if added_to_community:
            community = community_name

        filename = "-"

        if upload_result.get("files"):
            f = upload_result["files"][0]
            filename = f.get("key", f.get("filename", "-"))

            size = f.get("size")
            if size is not None:
                filesize = f"{size} bytes"

        record_url = (
            links.get("self_html")
            or links.get("latest_html")
            or links.get("self")
            or ""
        )

        html = f"""
        <html>
        <body style="
            margin:0;
            background:#f5f7fa;
            font-family:Arial,Helvetica,sans-serif;
        ">

        <div style="
            max-width:720px;
            margin:40px auto;
            background:white;
            border-radius:8px;
            box-shadow:0 2px 10px rgba(0,0,0,.08);
            padding:40px;
        ">

            <img src="cid:logo" width="200">

            <h2>Zenodo Upload Completed</h2>

            <div style="
                background:#eaf8ef;
                border-left:5px solid #2e7d32;
                padding:18px;
                margin:25px 0;
            ">
                <b>Upload successful</b><br>
                The dataset has been published successfully.
            </div>

            <table style="width:100%;border-collapse:collapse;">

                <tr>
                    <td><b>Title</b></td>
                    <td>{escape(title)}</td>
                </tr>

                <tr style="background:#f7f7f7;">
                    <td><b>Record ID</b></td>
                    <td>{record_id}</td>
                </tr>

                <tr>
                    <td><b>DOI</b></td>
                    <td>
                        <td>{escape(doi)}</td>
                    </td>
                </tr>

                <tr style="background:#f7f7f7;">
                    <td><b>Community</b></td>
                    <td>{escape(community)}</td>
                </tr>

                <tr>
                    <td><b>File</b></td>
                    <td>{escape(filename)}</td>
                </tr>

                <tr style="background:#f7f7f7;">
                    <td><b>Publication date</b></td>
                    <td>{escape(publication_date)}</td>
                </tr>

            </table>

            <div style="text-align:center;margin-top:40px;">
                <a href="{record_url}" style="
                    background:#1976d2;
                    color:white;
                    padding:14px 28px;
                    text-decoration:none;
                    border-radius:6px;
                    font-weight:bold;
                    display:inline-block;
                ">
                    Open Zenodo Record
                </a>
            </div>

        </div>
        <footer>If you encountered problems please reach us at {email_addr_from}</footer>
        </body>
        </html>
        """
    elif  mode == "community_success":
        metadata = upload_result.get("metadata", {})
        links = upload_result.get("links", {})

        title = upload_result.get("title", "-")
        record_id = upload_result.get("recid", upload_result.get("id", "-"))
        doi = upload_result.get("doi", "-")

        record_url = (
            links.get("self_html")
            or links.get("latest_html")
            or links.get("self")
            or ""
        )

        html = f"""
        <html>
        <body style="
            margin:0;
            background:#f5f7fa;
            font-family:Arial,Helvetica,sans-serif;
        ">

        <div style="
            max-width:720px;
            margin:40px auto;
            background:white;
            border-radius:8px;
            box-shadow:0 2px 10px rgba(0,0,0,.08);
            padding:40px;
        ">

            <img src="cid:logo" width="200">

            <h2>Community Association Completed</h2>

            <div style="
                background:#eaf8ef;
                border-left:5px solid #2e7d32;
                padding:18px;
                margin:25px 0;
            ">
                <b>Operation completed successfully.</b><br>
                The existing Zenodo record has been added to the
                <b>{escape(community_name)}</b> community.
            </div>

            <table style="width:100%;border-collapse:collapse;">

                <tr>
                    <td><b>Title</b></td>
                    <td>{escape(title)}</td>
                </tr>

                <tr style="background:#f7f7f7;">
                    <td><b>Record ID</b></td>
                    <td>{record_id}</td>
                </tr>

                <tr>
                    <td><b>DOI</b></td>
                    <td>{escape(doi)}</td>
                </tr>

                <tr style="background:#f7f7f7;">
                    <td><b>Community</b></td>
                    <td>{escape(community_name)}</td>
                </tr>

            </table>

            <p style="
                margin-top:30px;
                padding:15px;
                background:#f8f9fa;
                border-left:4px solid #1976d2;
            ">
                The metadata and files of the existing record have <b>not</b> been
                modified. Only the association with the
                <b>{escape(community_name)}</b> community has been created.
            </p>

            <div style="text-align:center;margin-top:35px;">
                <a href="{record_url}" style="
                    background:#1976d2;
                    color:white;
                    padding:14px 28px;
                    text-decoration:none;
                    border-radius:6px;
                    font-weight:bold;
                    display:inline-block;
                ">
                    Open Zenodo Record
                </a>
            </div>

        </div>

        <footer style="
            text-align:center;
            color:#777;
            font-size:13px;
            margin-top:20px;
        ">
            If you encounter any issues, please contact {email_addr_from}.
        </footer>

        </body>
        </html>
        """

    # FAILURE
    else:
        html = f"""
        <html>
        <body style="
            margin:0;
            background:#f5f7fa;
            font-family:Arial,Helvetica,sans-serif;
        ">

        <div style="
            max-width:720px;
            margin:40px auto;
            background:white;
            border-radius:8px;
            box-shadow:0 2px 10px rgba(0,0,0,.08);
            padding:40px;
        ">

            <img src="cid:logo" width="200">

            <h2>Zenodo Upload Failed</h2>

            <div style="
                background:#fdecea;
                border-left:5px solid #d32f2f;
                padding:18px;
                margin:25px 0;
            ">
                <b>The upload could not be completed.</b><br>
                The server returned an empty or invalid response.
            </div>

            <p>
                No record was created in Zenodo.
                Check logs for more details.
            </p>

        </div>
        </body>
        </html>
        """

    try:

        msg = MIMEMultipart("related")
        msg["From"] = email_addr_from
        msg["To"] = email_addr_receiver
        msg["Subject"] = subject

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(alt)

        logo_path = Path(__file__).parent / "logo.png"

        if logo_path.exists():
            with open(logo_path, "rb") as f:
                img = MIMEImage(f.read())

            img.add_header("Content-ID", "<logo>")
            img.add_header(
                "Content-Disposition",
                "inline",
                filename="logo.png",
            )

            msg.attach(img)

        with SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(email_addr_from, password)

            server.sendmail(
                email_addr_from,
                [email_addr_receiver, email_addr_from],
                msg.as_bytes(),
            )

        print(f"Email sent successfully to {email_addr_receiver}")

    except Exception as e:
        print(f"Error sending email: {e}")