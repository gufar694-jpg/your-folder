from flask import Flask, request, render_template_string
import sqlite3
import string, random
import qrcode
from io import BytesIO
import base64
import html

app = Flask(__name__)

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("links.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS links (short TEXT, original TEXT)")
    conn.commit()
    conn.close()

init_db()

def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


# ================= HOME PAGE =================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Text Tool</title>

<style>
body{margin:0;background:#f4f6f8;font-family:Arial;}
.box{max-width:420px;margin:10px auto;background:white;padding:15px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1);}
h2{text-align:center;color:#2e7d32;}

textarea{width:100%;padding:10px;border-radius:6px;border:1px solid #ccc;}

button{width:100%;padding:12px;margin-top:10px;background:#2e7d32;color:white;border:none;border-radius:8px;}

input{width:100%;padding:10px;margin-top:10px;border-radius:6px;border:1px solid #ccc;}

.qr{text-align:center;margin-top:10px;}
.qr img{width:200px;}

.btn2{margin-top:8px;background:#007bff;}
</style>
</head>

<body>

<div class="box">

<h2>🔗 Text Tool</h2>

<form method="POST">
<textarea name="note" rows="5" placeholder="Write text with # headings..." required></textarea>
<button type="submit">Generate Link</button>
</form>

{% if short_url %}
<input value="{{short_url}}" id="link" readonly>
<button onclick="copyLink()">Copy Link</button>

<div class="qr">
<img id="qrImg" src="data:image/png;base64,{{qr}}">
</div>

<button class="btn2" onclick="downloadQR()">Download QR</button>
<button class="btn2" onclick="shareQR()">Share QR</button>
{% endif %}

</div>

<script>
function copyLink(){
  var x=document.getElementById("link");
  x.select();
  document.execCommand("copy");
  alert("Copied!");
}

function downloadQR(){
  var img=document.getElementById("qrImg").src;
  var a=document.createElement("a");
  a.href=img;
  a.download="qr.png";
  a.click();
}

function shareQR(){
  var img=document.getElementById("qrImg").src;

  if(navigator.share){
    fetch(img)
    .then(res=>res.blob())
    .then(blob=>{
      var file=new File([blob],"qr.png",{type:"image/png"});
      navigator.share({
        files:[file],
        title:"QR Code"
      });
    });
  }else{
    alert("Sharing not supported");
  }
}
</script>

</body>
</html>
"""


# ================= HOME ROUTE =================
@app.route("/", methods=["GET","POST"])
def home():
    short_url=None
    qr_img=None

    if request.method=="POST":
        note=request.form["note"]
        code=generate_code()

        conn=sqlite3.connect("links.db")
        c=conn.cursor()
        c.execute("INSERT INTO links VALUES (?,?)",(code,note))
        conn.commit()
        conn.close()

        base=request.host_url.rstrip("/")
        short_url=f"{base}/{code}"

        qr=qrcode.make(short_url)
        buf=BytesIO()
        qr.save(buf,format="PNG")
        qr_img=base64.b64encode(buf.getvalue()).decode()

    return render_template_string(HTML,short_url=short_url,qr=qr_img)


# ================= NOTE VIEW =================
@app.route("/<code>")
def note(code):

    conn=sqlite3.connect("links.db")
    c=conn.cursor()
    c.execute("SELECT original FROM links WHERE short=?",(code,))
    row=c.fetchone()
    conn.close()

    if not row:
        return "Not Found"

    text=html.escape(row[0])
    lines=text.splitlines()

    out=""

    for line in lines:
        if line.startswith("### "):
            out+=f"<h3>{line[4:]}</h3>"
        elif line.startswith("## "):
            out+=f"<h2>{line[3:]}</h2>"
        elif line.startswith("# "):
            out+=f"<h1>{line[2:]}</h1>"
        elif line.strip()=="":
            out+="<div style='height:8px'></div>"
        else:
            out+=f"<p>{line}</p>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body{{margin:0;background:#e9ecef;font-family:Arial;}}

.wrap{{max-width:420px;margin:15px auto;padding:10px;}}

.note{{
background:white;
padding:14px;
border-radius:8px;
box-shadow:0 2px 8px rgba(0,0,0,0.15);
}}

h1{{font-size:17px;color:#2e7d32;margin:6px 0;}}
h2{{font-size:15px;color:#388e3c;margin:5px 0;}}
h3{{font-size:13px;color:#43a047;margin:4px 0;}}

p{{font-size:13px;line-height:1.5;margin:5px 0;color:#333;}}

.top{{display:flex;justify-content:space-between;margin-bottom:8px;}}

.btn{{background:#2e7d32;color:white;border:none;padding:5px 8px;border-radius:5px;font-size:11px;margin-left:5px;}}

.actions{{display:flex;gap:5px;}}
</style>

</head>

<body>

<div class="wrap">

<div class="top">
<b style="color:#2e7d32;">📄 Note</b>

<div class="actions">
<button class="btn" onclick="copyText()">Copy</button>
<button class="btn" onclick="downloadPDF()">PDF</button>
</div>

</div>

<div class="note" id="text">
{out}
</div>

</div>

<script>
function copyText(){{
var t=document.getElementById("text").innerText;
navigator.clipboard.writeText(t);
alert("Copied!");
}}

function downloadPDF(){{
window.print();
}}
</script>

</body>
</html>
"""


# ================= RUN =================
if __name__=="__main__":
    app.run(debug=True)
