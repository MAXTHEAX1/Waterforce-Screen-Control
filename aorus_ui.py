"""The page shown in the Waterforce Screen Control window (served by aorus_lcd_app.py). Plain HTML/CSS/JS in one string."""

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" type="image/png" sizes="16x16" data-n="16" href="/icon/16.png">
<link rel="icon" type="image/png" sizes="32x32" data-n="32" href="/icon/32.png">
<link rel="icon" type="image/png" sizes="64x64" data-n="64" href="/icon/64.png">
<link rel="icon" type="image/png" sizes="256x256" data-n="256" href="/icon/256.png">
<title>Waterforce Screen Control</title>
<style>
:root{--bg:#0d0f14;--panel:#151922;--panel2:#1b212d;--line:#262d3b;--text:#e8ebf2;--dim:#8b93a7;
--accent:#ff6a1a;--accent2:#ffb347;--accent-rgb:255,106,26;--on-accent:#1a0a00;--good:#3ddc84;--bad:#ff5468;--r:14px}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);
font:14px/1.45 "Segoe UI",system-ui,sans-serif;overflow:hidden}
body{display:flex}
nav{width:200px;background:var(--panel);border-right:1px solid var(--line);padding:18px 12px;display:flex;flex-direction:column;gap:4px}
.brand{display:flex;flex-direction:column;align-items:center;gap:8px;padding:2px 4px 18px;font-weight:600;font-size:14px;line-height:1.2;text-align:center}
.brand img{width:104px;height:104px;object-fit:contain;flex:none}
.brand i{width:26px;height:26px;border-radius:50%;border:4px solid var(--accent);display:block;position:relative}
.brand i:after{content:"";position:absolute;inset:4px;border-radius:50%;background:var(--accent)}
nav button{all:unset;cursor:pointer;padding:10px 12px;border-radius:10px;color:var(--dim);display:flex;gap:10px;align-items:center}
nav button:hover{background:var(--panel2);color:var(--text)}
nav button.on{background:linear-gradient(90deg,rgba(var(--accent-rgb),.22),rgba(var(--accent-rgb),.04));color:var(--text);box-shadow:inset 3px 0 var(--accent)}
.conn{margin-top:auto;padding:10px;border-radius:10px;background:var(--panel2);font-size:12px;color:var(--dim)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--bad);margin-right:6px}
.dot.ok{background:var(--good);box-shadow:0 0 8px var(--good)}
main{flex:1;overflow:auto;padding:26px 30px 60px}
h1{margin:0 0 4px;font-size:22px}
.sub{color:var(--dim);margin:0 0 22px}
.grid{display:grid;gap:14px}
.cards{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:16px}
.card h3{margin:0 0 10px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);font-weight:600}
.big{font-size:30px;font-weight:600}
.big small{font-size:14px;color:var(--dim);font-weight:400}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start}
.btn{all:unset;cursor:pointer;padding:9px 16px;border-radius:10px;background:var(--panel2);border:1px solid var(--line);color:var(--text);font-weight:500}
.btn:hover{border-color:var(--accent)}
.btn.pri{background:var(--accent);border-color:var(--accent);color:var(--on-accent);font-weight:600}
.btn.pri:hover{filter:brightness(1.1)}
.btn.bad:hover{border-color:var(--bad);color:var(--bad)}
.btn[disabled],.btn.dis{opacity:.4;pointer-events:none}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.tile{cursor:pointer;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:14px;transition:.15s}
.tile:hover{border-color:var(--accent);transform:translateY(-1px)}
.tile.on{border-color:var(--accent);background:linear-gradient(160deg,rgba(var(--accent-rgb),.18),var(--panel))}
.tile b{display:block;margin-bottom:2px}.tile span{color:var(--dim);font-size:12px}
.seg{display:flex;flex-wrap:wrap;gap:8px}
.seg button{all:unset;cursor:pointer;padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel2);color:var(--dim)}
.seg button.on{background:var(--accent);color:var(--on-accent);border-color:var(--accent);font-weight:600}
input[type=text],select,input[type=number]{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 12px;font:inherit;min-width:0}
input[type=text]:focus,select:focus{outline:none;border-color:var(--accent)}
input[type=color]{width:54px;height:40px;border:1px solid var(--line);background:var(--panel2);border-radius:10px;padding:3px;cursor:pointer}
label.sw{display:flex;gap:12px;align-items:center;cursor:pointer;padding:6px 0}
label.sw input{accent-color:var(--accent);width:18px;height:18px}
.list{display:flex;flex-direction:column;gap:8px}
.item{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.item.on{border-color:var(--accent)}
.item .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sect{margin:26px 0 10px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);font-weight:600}
.hint{color:var(--dim);font-size:12.5px}
.warn{color:var(--warn,var(--accent2))}
.err{color:var(--bad)}
.bar{height:8px;border-radius:99px;background:var(--panel2);overflow:hidden}
pre.logbox{margin:10px 0 0;padding:10px 12px;max-height:220px;overflow:auto;background:var(--panel2);border:1px solid var(--line);border-radius:10px;
font:12px/1.5 Consolas,"Cascadia Mono",monospace;white-space:pre-wrap;word-break:break-word;user-select:text;color:var(--text)}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));width:0;transition:width .3s}
#banner{position:fixed;left:200px;right:0;top:0;padding:10px 30px;background:var(--panel2);border-bottom:1px solid var(--accent);display:none;z-index:5}
#toasts{position:fixed;right:18px;bottom:18px;display:flex;flex-direction:column;gap:8px;z-index:9}
.toast{background:var(--panel2);border:1px solid var(--line);border-left:4px solid var(--good);border-radius:10px;padding:10px 14px;max-width:420px;animation:in .2s}
.toast.error{border-left-color:var(--bad)}
@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
.lcd{width:230px;height:230px;border-radius:50%;background:#050608;border:6px solid #232a38;box-shadow:0 0 0 2px #0a0c10,0 0 40px rgba(var(--accent-rgb),.18);
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;flex:none;overflow:hidden}
.lcd{color:#e8ebf2}.lcd .v{font-size:56px;font-weight:700}.lcd .l{font-size:12px;letter-spacing:.14em;color:#8b93a7;text-transform:uppercase}.lcd .item2{font-size:13px;color:#cfd5e3;line-height:1.5}.lcd .off{font-size:12px;color:#5d6578}
.lcd .two{display:flex;gap:18px}.lcd .two .v{font-size:34px}
.pad{display:grid;grid-template-columns:repeat(3,34px);gap:4px}
.pad button{all:unset;cursor:pointer;width:34px;height:34px;border-radius:8px;background:var(--panel2);border:1px solid var(--line);text-align:center;line-height:34px;color:var(--dim)}
.pad button:hover{border-color:var(--accent)}.pad button.on{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
input[type=range]{accent-color:var(--accent);width:100%}
textarea{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 12px;font:inherit;width:100%;resize:vertical}
textarea:focus{outline:none;border-color:var(--accent)}
.pv{position:relative;width:260px;height:260px;border-radius:12px;overflow:hidden;border:1px solid var(--line);flex:none;background:#000}
.pv img{width:100%;height:100%;display:block;image-rendering:auto}
.pv:after{content:"";position:absolute;inset:6px;border-radius:50%;border:1px dashed rgba(255,255,255,.28);pointer-events:none}
.field{margin-bottom:12px}.field>.hint{margin-bottom:4px}
.sw2{width:34px;height:34px;border-radius:50%;border:2px solid var(--line);cursor:pointer;padding:0}
.sw2:hover{border-color:var(--text)}
.checks{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:2px 14px}
.lcd img{width:100%;height:100%;object-fit:cover;display:block}
.thumb{width:44px;height:44px;border-radius:8px;object-fit:cover;flex:none;background:#000}
details summary{cursor:pointer;color:var(--dim);margin:8px 0}
.page{display:none}.page.on{display:block}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.tip{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;margin-left:6px;border-radius:50%;border:1px solid var(--dim);color:var(--dim);
font:700 10.5px/1 "Segoe UI",system-ui,sans-serif;font-style:normal;text-transform:none;letter-spacing:0;cursor:help;vertical-align:middle;flex:none;user-select:none;position:relative;top:-1px}
.tip:hover,.tip:focus-visible,.tip.pin{color:var(--on-accent);background:var(--accent);border-color:var(--accent);outline:none}
label.sw .tip{margin-left:-4px}
.inl{display:inline-flex;align-items:center}
#bubble{position:fixed;z-index:30;left:0;top:0;width:max-content;max-width:300px;padding:10px 13px;border-radius:10px;background:var(--panel2);border:1px solid var(--accent);
box-shadow:0 10px 30px rgba(0,0,0,.45);color:var(--text);font-size:12.5px;line-height:1.5;font-weight:400;text-transform:none;letter-spacing:0;white-space:pre-line;
pointer-events:none;opacity:0;visibility:hidden;transition:opacity .12s}
#bubble.show{opacity:1;visibility:visible}
#bubble:after{content:"";position:absolute;left:var(--ax,20px);width:10px;height:10px;margin-left:-5px;background:var(--panel2);border:1px solid var(--accent);transform:rotate(45deg)}
#bubble.below:after{top:-6px;border-right:0;border-bottom:0}
#bubble.above:after{bottom:-6px;border-left:0;border-top:0}
@media(max-width:900px){.two-col{grid-template-columns:1fr}nav{width:64px}.brand img{width:40px;height:40px}nav span.t,.brand b,.conn{display:none}#banner{left:64px}}
</style></head>
<body>
<nav>
 <div class="brand"><img id="brandimg" alt="" src="/logo.png"><b>Waterforce<br>Screen Control</b></div>
 <button data-p="dash" class="on">◉ <span class="t">Dashboard</span></button>
 <button data-p="screens">▦ <span class="t">Screens</span></button>
 <button data-p="media">▶ <span class="t">GIFs &amp; Pictures</span></button>
 <button data-p="text">Aa <span class="t">Text</span></button>
 <button data-p="settings">⚙ <span class="t">Settings</span></button>
 <div class="conn"><span id="cdot" class="dot"></span><span id="ctext">Connecting...</span></div>
</nav>
<div id="banner"></div>
<main>
<!-- DASHBOARD -->
<section class="page on" id="p-dash">
 <h1>Dashboard</h1><p class="sub" id="nowshowing" style="margin-bottom:6px">&nbsp;</p>
 <p class="hint" style="margin:0 0 20px">New here? Look for the <x-tip k="howto"></x-tip> bubbles. Hover over one (or click it) to see what a setting does.</p>
 <div class="row" style="align-items:center;margin-bottom:18px">
  <div style="text-align:center"><div class="lcd" id="lcd"></div><div class="hint" style="margin-top:8px">Screen preview<x-tip k="lcd"></x-tip></div></div>
  <div class="grid cards" style="flex:1;min-width:300px">
   <div class="card"><h3>CPU<x-tip k="cpu"></x-tip></h3><div class="big" id="s-cpu">–<small> °C</small></div></div>
   <div class="card"><h3>VRM<x-tip k="vrm"></x-tip></h3><div class="big" id="s-vrm">–<small> °C</small></div></div>
   <div class="card"><h3>Liquid<x-tip k="liq"></x-tip></h3><div class="big" id="s-liq">–<small> °C</small></div></div>
   <div class="card"><h3>Fan<x-tip k="fan"></x-tip></h3><div class="big" id="s-fan">–<small> rpm</small></div></div>
   <div class="card"><h3>Pump<x-tip k="pump"></x-tip></h3><div class="big" id="s-pump">–<small> rpm</small></div></div>
  </div>
 </div>
 <div class="card" id="lhmcard"></div>
</section>
<!-- SCREENS -->
<section class="page" id="p-screens">
 <h1>Screens</h1><p class="sub">Pick what the cooler shows. Everything here is remembered and restored the next time the app starts.<x-tip k="tiles"></x-tip></p>
 <div class="tiles" id="tiles"></div>
 <div class="sect">What the screen shows</div>
 <div class="card" id="optcard"></div>
 <div class="sect">Temperature unit<x-tip k="unit"></x-tip></div>
 <div class="card"><div class="row" style="align-items:center">
  <div class="seg unitseg"><button data-u="C">°C &nbsp;Celsius</button><button data-u="F">°F &nbsp;Fahrenheit</button></div>
  <span class="hint">Used on every screen that shows a temperature, and in this app.</span></div></div>
 <div class="sect">Colors<x-tip k="colors"></x-tip></div>
 <div class="card"><div class="row" style="align-items:center">
  <div id="z1box"><div class="hint" id="z1lbl">Zone 1</div><input type="color" id="col1" value="#ff6a1a"></div>
  <div id="z2box"><div class="hint" id="z2lbl">Zone 2</div><input type="color" id="col2" value="#ffffff"></div>
  <button class="btn pri" id="applycol">Apply colors</button>
  <span class="hint" id="colhint"></span></div></div>
</section>
<!-- MEDIA -->
<section class="page" id="p-media">
 <h1>GIFs &amp; Pictures</h1><p class="sub">Files stored on the cooler itself (about 40 MB in total).<x-tip k="mstore"></x-tip></p>
 <div class="seg" id="mseg" style="margin-bottom:16px"><button data-w="gif" class="on">GIFs / videos</button><button data-w="pic">Pictures</button></div>
 <div class="row" style="margin-bottom:12px;align-items:center">
  <span class="inl"><button class="btn" id="mrefresh">⟳ Load list from cooler</button><x-tip k="mload"></x-tip></span>
  <span class="inl"><button class="btn pri" id="mpick">＋ Add file</button><x-tip k="madd"></x-tip></span>
  <input type="file" id="mfile" style="display:none">
 </div>
 <div class="card" id="mopts" style="margin-bottom:14px"></div>
 <div id="mprog" style="display:none;margin-bottom:14px"><div class="hint" id="mproglabel"></div><div class="bar"><i id="mprogbar"></i></div></div>
 <div class="list" id="mlist"></div>
</section>
<!-- TEXT -->
<section class="page" id="p-text">
 <h1>Text</h1><p class="sub">Show your own message on the screen. The preview is exactly what gets sent (the dashed circle is roughly the visible round area).</p>
 <div class="row">
  <div style="flex:1;min-width:300px">
   <div class="card">
    <div class="field"><div class="hint">Message (up to 80 characters, Enter starts a new line)<x-tip k="tmsg"></x-tip></div><textarea id="txt" rows="3" maxlength="80" placeholder="HELLO"></textarea></div>
    <div class="row">
     <div class="field"><div class="hint">Text color</div><input type="color" id="t-color" value="#ffffff"></div>
     <div class="field"><div class="hint">Background</div><input type="color" id="t-bg" value="#000000"></div>
     <div class="field" style="flex:1;min-width:150px"><div class="hint">Font<x-tip k="tfont"></x-tip></div><select id="t-font" style="width:100%">
      <option value="arial">Arial</option><option value="arial-bold">Arial Bold</option><option value="segoe">Segoe UI</option><option value="segoe-bold">Segoe UI Bold</option>
      <option value="verdana">Verdana</option><option value="consolas">Consolas</option><option value="impact">Impact</option><option value="times">Times New Roman</option></select>
      <div class="row" style="margin-top:6px;gap:8px"><button class="btn" id="font-add" type="button">Add font file (.ttf)...</button><button class="btn bad" id="font-del" type="button" style="display:none">Remove this font</button><input type="file" id="font-file" accept=".ttf,.otf,.ttc" style="display:none"></div></div>
    </div>
    <div class="field"><div class="hint">Size: <b id="t-sizev">56</b><x-tip k="tsize"></x-tip></div><input type="range" id="t-size" min="12" max="200" value="56"></div>
    <div class="row" style="align-items:center">
     <div class="field"><div class="hint">Position<x-tip k="tpos"></x-tip></div><div class="pad" id="t-pad"></div></div>
     <div class="field" style="flex:1;min-width:200px"><div class="hint">Left / right: <b id="t-xv">0</b></div><input type="range" id="t-x" min="-160" max="160" value="0">
      <div class="hint" style="margin-top:8px">Up / down: <b id="t-yv">0</b></div><input type="range" id="t-y" min="-160" max="160" value="0">
      <div class="hint" style="margin-top:8px">Slant: <b id="t-sv">0</b>° (negative leans left)<x-tip k="tslant"></x-tip></div><input type="range" id="t-slant" min="-45" max="45" value="0">
      <div class="hint" style="margin-top:8px">Rotate: <b id="t-rv">0</b>° (positive turns clockwise)<x-tip k="trot"></x-tip></div><input type="range" id="t-rot" min="-180" max="180" value="0"></div>
    </div>
    <div class="row" style="align-items:center"><span class="inl"><button class="btn pri" id="txtsend">Send to cooler</button><x-tip k="tsend"></x-tip></span><button class="btn" id="t-reset">Reset position, slant &amp; rotation</button></div>
   </div>
  </div>
  <div class="pv"><img id="t-prev" alt="preview"></div>
 </div>
</section>
<!-- SETTINGS -->
<section class="page" id="p-settings">
 <h1>Settings</h1><p class="sub">Make this app replace Gigabyte Control Center.</p>
 <div class="two-col">
 <div class="card"><h3>Startup</h3>
  <label class="sw"><input type="checkbox" id="set-auto"> Start with Windows (hidden in the tray)<x-tip k="auto"></x-tip></label>
  <label class="sw"><input type="checkbox" id="set-apply"> Restore my last screen when the app starts<x-tip k="apply"></x-tip></label>
  <p class="hint warn" id="autohint" style="display:none"></p>
 </div>
 <div class="card"><h3>LibreHardwareMonitor (the temperature reader)<x-tip k="lhmcard"></x-tip></h3>
  <p class="hint" style="margin-top:0">This app needs LibreHardwareMonitor running in the background to read your CPU and VRM temperatures. One button downloads it if needed (with its sensor driver), turns on its data feed and starts it for you at every login.</p>
  <div id="lhmstatus" style="margin-bottom:10px"></div>
  <div class="row" style="align-items:center"><span class="inl"><button class="btn pri" id="lhm-setup">Set up LibreHardwareMonitor for me</button><x-tip k="lhmsetup"></x-tip></span><span class="inl"><button class="btn" id="lhmtask-off">Turn off its automatic start</button><x-tip k="lhmoff"></x-tip></span></div>
  <div id="lhminst"></div>
  <p class="hint" id="lhmtaskhint"></p>
  <details><summary>Use my own copy instead</summary>
   <div class="hint">Path to LibreHardwareMonitor.exe<x-tip k="lhmown"></x-tip></div>
   <div class="row" style="margin:6px 0"><input type="text" id="set-lhmpath" style="flex:1" placeholder="C:\Tools\LibreHardwareMonitor\LibreHardwareMonitor.exe"><button class="btn" id="save-lhm">Save</button></div>
   <label class="sw"><input type="checkbox" id="set-launch"> Start it for me if it isn't running</label>
  </details>
 </div>
 <div class="card"><h3>Temperatures</h3>
  <div class="hint">Show temperatures in<x-tip k="unit"></x-tip></div>
  <div class="seg unitseg" style="margin:6px 0 14px"><button data-u="C">°C &nbsp;Celsius</button><button data-u="F">°F &nbsp;Fahrenheit</button></div>
  <div class="hint">CPU sensor<x-tip k="cpusens"></x-tip></div><select id="set-cpu" style="width:100%;margin:6px 0 12px"></select>
  <div class="hint">VRM sensor - choose the motherboard sensor for your VRM/MOSFET (if none is chosen the cooler shows a fixed 36)<x-tip k="vrmsens"></x-tip></div><select id="set-vrm" style="width:100%;margin:6px 0"></select>
 </div>
 <div class="card"><h3>Appearance<x-tip k="appear"></x-tip></h3>
  <div class="row" style="align-items:center;margin-bottom:10px"><div><div class="hint">Accent color</div><input type="color" id="th-accent"></div>
   <div style="flex:1"><div class="hint">Quick picks</div><div class="row" style="gap:8px" id="th-acc-sw"></div></div></div>
  <div class="row" style="align-items:center;margin-bottom:10px"><div><div class="hint">Background</div><input type="color" id="th-bg"></div>
   <div style="flex:1"><div class="hint">Quick picks</div><div class="row" style="gap:8px" id="th-bg-sw"></div></div></div>
  <button class="btn" id="th-reset">Back to the default look</button>
 </div>
 <div class="card"><h3>App logo<x-tip k="logo"></x-tip></h3>
  <div class="row" style="align-items:center"><img id="logoprev" alt="" src="/logo.png" style="width:64px;height:64px;object-fit:contain"><div id="nologo" class="hint">Using the built-in Waterforce logo.</div></div>
  <div class="row" style="margin-top:10px"><button class="btn pri" id="logo-pick">Use a different logo...</button><button class="btn" id="logo-del">Back to the built-in logo</button><input type="file" id="logo-file" accept="image/*" style="display:none"></div>
  <p class="hint" style="margin-bottom:0">Shows in the sidebar, the window icon and the tray. A square PNG with a transparent background works best.</p>
 </div>
 </div>
 <div class="sect">App</div>
 <span class="inl"><button class="btn bad" id="quit">Quit the app completely</button><x-tip k="quit"></x-tip></span>
 <p class="hint">Closing this window leaves the app running in the tray so your screen keeps updating. Quit stops the temperature feed.</p>
</section>
</main>
<div id="toasts"></div>
<div id="bubble" role="tooltip"></div>
<script>
const TOKEN="__TOKEN__";
const THEME0=__THEME__;
function h2r(h){h=h.replace("#","");return [0,2,4].map(i=>parseInt(h.substr(i,2),16))}
function r2h(c){return "#"+c.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,"0")).join("")}
function mixc(a,b,t){return a.map((v,i)=>v+(b[i]-v)*t)}
function lumi(c){const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])}
function applyTheme(t){
  const bg=h2r(t.bg),ac=h2r(t.accent),dark=lumi(bg)<.4,fg=dark?[255,255,255]:[0,0,0],txt=dark?[232,235,242]:[26,29,36];
  const r=document.documentElement.style;
  r.setProperty("--bg",t.bg);r.setProperty("--panel",r2h(mixc(bg,fg,.05)));r.setProperty("--panel2",r2h(mixc(bg,fg,.10)));
  r.setProperty("--line",r2h(mixc(bg,fg,.18)));r.setProperty("--text",r2h(txt));r.setProperty("--dim",r2h(mixc(bg,txt,.58)));
  r.setProperty("--accent",t.accent);r.setProperty("--accent2",r2h(mixc(ac,[255,255,255],.35)));r.setProperty("--accent-rgb",ac.join(","));
  r.setProperty("--on-accent",lumi(ac)>.35?"#14100c":"#ffffff");
  r.setProperty("--bad",dark?"#ff5468":"#c4283c");r.setProperty("--good",dark?"#3ddc84":"#1b9a55");r.setProperty("--warn",dark?r2h(mixc(ac,[255,255,255],.35)):"#a14a00");
  r.setProperty("color-scheme",dark?"dark":"light");
}
applyTheme(THEME0);
let S=null, SYS=null, curPage="dash", mediaTab="gif", selScreen=null, seenEv=0, firstState=true, busyUpload=false;
const SCREENS=[[1,"Enthusiast 01","Numbers & color"],[2,"Enthusiast 02","Two zone colors"],[3,"Enthusiast 03","Two zone colors"],[4,"Enthusiast 04","Choose sensors"],[6,"Function","Pick what to show"]];
const FITEMS=[["model","CPU model"],["fan","Fan RPM"],["pump","Pump RPM"],["temp","CPU temp"],["liquid","Liquid temp"],["clocks","CPU clocks"],["threads","CPU threads"]];
const INTERVALS=[2,3,5,10,15,30];
function defCfg(sc){return sc===4?{numbers:true,sensors:"cpu"}:sc===6?{numbers:true,items:["fan","pump","temp","liquid","clocks","threads"],interval:5}:{numbers:true,model:false,metric:"temp"}}
function cfgOf(sc){return Object.assign(defCfg(sc),(S&&S.settings.screen_cfg&&S.settings.screen_cfg[sc])||{})}
function zonesOf(sc,cfg){if(sc===2||sc===3)return [1,2];if(sc===4)return cfg.numbers&&cfg.sensors.includes("-")?[1,2]:[2];return [1]}
const S4={"cpu":"CPU","liquid":"Liquid","vrm":"VRM","cpu-liquid":"CPU + Liquid","cpu-vrm":"CPU + VRM","liquid-vrm":"Liquid + VRM"};
const $=id=>document.getElementById(id);
const _h={};function setHTML(id,h){if(_h[id]!==h){_h[id]=h;$(id).innerHTML=h;return true}return false}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
async function api(path,body){
  try{const r=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"X-Token":TOKEN,"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});
  return await r.json();}catch(e){return {ok:false,error:"The app isn't responding."}}
}
function toast(t,level){const d=document.createElement("div");d.className="toast "+(level||"");d.textContent=t;$("toasts").appendChild(d);setTimeout(()=>d.remove(),level==="error"?9000:4000)}
async function act(path,body,okmsg){const r=await api(path,body);if(r&&r.ok===false)toast(r.error||"Failed","error");else if(okmsg)toast(okmsg);return r}

/* ---- help bubbles: every text lives here, so it is easy to reword */
const TIPS={
 howto:"Like this! These little bubbles explain what a setting does, in plain English.",
 lcd:"A small picture of what the cooler's screen is showing right now. For the number screens it is a simple drawing that updates live. For pictures, animations and text it shows your actual file.",
 cpu:"Your processor's temperature. This app reads it through LibreHardwareMonitor and sends it to the cooler every couple of seconds so the screen can show it.",
 vrm:"The temperature of the power chips next to your processor (the VRM). Every motherboard names this sensor differently, so if you see a dash, choose yours in Settings, under Temperatures.",
 liq:"The temperature of the liquid inside the cooler. The cooler measures this itself, so it doesn't come from LibreHardwareMonitor.",
 fan:"How fast the radiator fans are spinning, in revolutions per minute (rpm), as reported by the cooler.",
 pump:"How fast the pump inside the cooler is spinning, in revolutions per minute (rpm).",
 lhm:"LibreHardwareMonitor is a free program that reads your PC's sensors. This app needs it to find out your CPU temperature. If it isn't installed or running, a button here sets it up for you.",
 tiles:"Each tile is one of the cooler's built-in screen styles. Click a tile to switch the cooler to it. Your choices for each screen are remembered.",
 numbers:"Untick this to hide every reading, so the screen shows only its background design with no numbers or text on it.",
 model:"Shows the name of your processor on the screen. Only Enthusiast 01 shows it reliably. Enthusiast 02 and 03 may show a generic placeholder instead (Gigabyte's own software does the same).",
 metric:"Choose the one reading to show: your CPU temperature, how fast your CPU is running right now (clocks), or nothing.",
 sens:"Choose which temperature fills the screen. One sensor uses the whole screen. Two sensors split it in half, and each half gets its own color.",
 items:"Tick everything you want to see. The screen shows one item at a time and moves on to the next automatically, round and round.",
 interval:"How long each item stays up before the next one appears. It is approximate (within about a second) because the cooler counts in small steps of roughly 1.65 seconds.",
 unit:"Choose whether temperatures are shown in Celsius (°C) or Fahrenheit (°F), both on the cooler's screens and in this app. Your PC's real temperatures don't change, only how they are written.",
 colors:"Pick the colors this screen uses, then press Apply colors. Some screens have two color zones, so you'll see two pickers. Others have just one.",
 mstore:"These files are saved on the cooler itself (about 40 MB in total), not on your PC.",
 mload:"Asks the cooler which files it has saved so they show up in the list below. Do it once after starting the app. The screen briefly switches while it loads.",
 madd:"Choose a GIF or video from your PC (or a picture, on the Pictures tab). The app resizes it to fit the round screen and sends it to the cooler.",
 fill:"The cooler goes dark for a moment each time a file reaches its end and starts over. To hide that, a short GIF is repeated inside one file until it lasts about this many seconds. Bigger numbers mean fewer blips but a bigger file. 0 turns it off.",
 maxclip:"Longer videos are cut off after this many seconds, so the file stays small enough for the cooler.",
 fit:"Crop to fill zooms the picture so it covers the whole round screen (the edges get trimmed). Fit with black bars shows the whole picture with black borders around it.",
 tmsg:"Type what you want on the screen. The text is turned into a picture and sent to the cooler. The screen is round, so keep the important words toward the middle (inside the dashed circle in the preview).",
 tfont:"Choose a font. To use your own, press Add font file and pick a .ttf or .otf file from your PC. It is saved inside this app and appears under Your fonts.",
 tsize:"How big the letters are. Very large text can run off the edge of the round screen.",
 tpos:"Moves the text around the screen. Click a dot for a quick position, or use the sliders for fine control.",
 tslant:"Leans the letters to the right or left, like italics. 0 is upright.",
 trot:"Turns the whole text around its center. Positive numbers turn it clockwise.",
 tsend:"Sends the text to the cooler and switches to it. What you see in the preview is exactly what the cooler will show.",
 auto:"Starts this app by itself every time you log in to Windows, hidden in the tray (the little icons near the clock), so the cooler always gets temperatures.",
 apply:"When the app starts, it puts back whatever the cooler was showing last time.",
 lhmcard:"LibreHardwareMonitor is a free, open-source program that reads your PC's sensors. This app uses it to find out your CPU and VRM temperatures.",
 lhminstall:"Downloads LibreHardwareMonitor (a free, open-source sensor reader) and its small sensor driver from their official GitHub pages, turns on its data feed, and makes it start by itself at every login. Needs an internet connection. Windows asks for permission once.",
 lhmsetup:"Downloads LibreHardwareMonitor and its sensor driver if they aren't on this PC yet, turns on its data feed, and makes it start by itself at every login. Windows asks for permission once. It is safe to press again if something stops working.",
 lhmoff:"Stops LibreHardwareMonitor from starting by itself at login. Without it running, the cooler can't get your CPU temperature.",
 lhmown:"Only needed if you already have LibreHardwareMonitor somewhere on your PC. Point the app at its .exe file.",
 cpusens:"Which reading counts as your CPU temperature. Leave it on Automatic unless the number looks wrong.",
 vrmsens:"VRM means the power chips beside your processor. Motherboards name this sensor differently, so pick yours from the list. If none is chosen, the cooler shows a fixed 36.",
 appear:"Changes the colors of this app. It doesn't change the cooler's screen.",
 logo:"Replaces the logo shown in the sidebar, the window icon and the tray with your own picture.",
 quit:"Closing the window only hides it in the tray, so your cooler keeps getting temperatures. Quit stops the app completely."
};
function tip(k){return '<span class="tip" tabindex="0" role="button" aria-label="More information" data-t="'+k+'">i</span>'}
document.querySelectorAll("x-tip").forEach(e=>{e.outerHTML=tip(e.getAttribute("k"))});
(function(){
  const bub=$("bubble");let cur=null,pinned=null;
  function place(el){
    const txt=TIPS[el.dataset.t];if(!txt)return false;
    bub.textContent=txt;bub.classList.remove("below","above");bub.style.left="0px";bub.style.top="0px";
    const r=el.getBoundingClientRect(),bw=bub.offsetWidth,bh=bub.offsetHeight,vw=document.documentElement.clientWidth,vh=document.documentElement.clientHeight;
    const cx=r.left+r.width/2,left=Math.max(8,Math.min(vw-bw-8,Math.round(cx-bw/2)));
    let top=Math.round(r.bottom+10),pos="below";
    if(top+bh>vh-8&&r.top-bh-10>8){top=Math.round(r.top-bh-10);pos="above"}
    bub.style.left=left+"px";bub.style.top=top+"px";
    bub.style.setProperty("--ax",Math.max(14,Math.min(bw-14,Math.round(cx-left)))+"px");bub.classList.add(pos);return true}
  function show(el){if(place(el)){cur=el;bub.classList.add("show")}}
  function hide(){cur=null;bub.classList.remove("show")}
  function unpin(){if(pinned){pinned.classList.remove("pin");pinned=null}}
  function toggle(t){if(pinned===t){unpin();hide()}else{unpin();pinned=t;t.classList.add("pin");show(t)}}
  const tipOf=e=>e.target&&e.target.closest?e.target.closest(".tip"):null;
  document.addEventListener("mouseover",e=>{const t=tipOf(e);if(t&&!pinned)show(t)});
  document.addEventListener("mouseout",e=>{const t=tipOf(e);if(t&&!pinned&&!(e.relatedTarget&&t.contains(e.relatedTarget)))hide()});
  document.addEventListener("focusin",e=>{const t=tipOf(e);if(t&&!pinned)show(t)});
  document.addEventListener("focusout",()=>{if(!pinned)hide()});
  document.addEventListener("click",e=>{const t=tipOf(e);
    if(t){e.preventDefault();e.stopPropagation();toggle(t);return}
    if(pinned){unpin();hide()}},true);
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){unpin();hide();return}
    if(e.key==="Enter"||e.key===" "){const t=tipOf(e);if(t){e.preventDefault();toggle(t)}}});
  window.addEventListener("resize",()=>{unpin();hide()});
  document.querySelector("main").addEventListener("scroll",()=>{unpin();hide()},{passive:true});
  setInterval(()=>{if(cur&&!document.body.contains(cur)){unpin();hide()}},300);
})();

/* ---- temperature unit (the readings are always Celsius inside the app; this only changes how they are shown) */
let UNIT="C",unitLock=0;
function cvt(v){return UNIT==="F"?v*9/5+32:v}
function renderUnit(){document.querySelectorAll(".unitseg button").forEach(b=>b.classList.toggle("on",b.dataset.u===UNIT))}
function setUnit(u){if(u===UNIT)return;UNIT=u;unitLock=Date.now()+3000;renderUnit();if(S)render();act("/api/unit",{unit:u})}
document.querySelectorAll(".unitseg button").forEach(b=>b.onclick=()=>setUnit(b.dataset.u));
renderUnit();

document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{
  curPage=b.dataset.p;document.querySelectorAll("nav button").forEach(x=>x.classList.toggle("on",x===b));
  document.querySelectorAll(".page").forEach(p=>p.classList.toggle("on",p.id==="p-"+curPage));
  if(curPage==="settings")loadSystem();render();
});

function temp(v){return v==null?"–":Math.round(cvt(v))}
function modeText(m){
  if(!m)return "Nothing chosen yet";
  if(m.kind==="temp"){const n=SCREENS.find(s=>s[0]===m.screen);let t="Showing "+(n?n[1]:"screen "+m.screen);const c=cfgOf(m.screen);if(!c.numbers)t+=" (numbers off)";else if(m.screen===4)t+=" ("+S4[c.sensors]+")";return t}
  if(m.kind==="text")return "Showing text: "+m.text.replace(/\n/g," / ");
  return m.kind==="gif"?"Playing your animation":"Showing your picture";
}
function renderLcd(){
  const r=S.readings,m=S.mode;let h="";
  if(m&&m.kind==="temp"){
    const sc=m.screen,c=cfgOf(sc);
    if(!c.numbers){h='<div class="off">numbers off</div>'}
    else if(sc===4){
      const parts=c.sensors.split("-").map(k=>[k,k==="cpu"?r.cpu:k==="vrm"?r.vrm:r.liquid]);
      if(parts.length===2)h='<div class="two">'+parts.map(p=>'<div><div class="v">'+temp(p[1])+'°</div><div class="l">'+p[0]+'</div></div>').join("")+'</div>';
      else h='<div class="l">'+parts[0][0]+'</div><div class="v">'+temp(parts[0][1])+'°</div>';
    }else if(sc===6){
      const val={model:"CPU",fan:(r.fan==null?"–":r.fan)+" rpm fan",pump:(r.pump==null?"–":r.pump)+" rpm pump",temp:"CPU "+temp(r.cpu)+"°",liquid:"Liquid "+temp(r.liquid)+"°",clocks:"clocks",threads:"threads"};
      h=c.items.length?'<div class="item2">'+c.items.map(i=>val[i]).join("<br>")+'</div>':'<div class="off">nothing ticked</div>';
    }else{
      h=(c.model?'<div class="l">CPU</div>':"")+(c.metric==="temp"?'<div class="v">'+temp(r.cpu)+'°</div>':c.metric==="clocks"?'<div class="l" style="margin-top:6px">clocks</div>':"");
      if(!h)h='<div class="off">no numbers</div>';
    }
  }else if(m&&m.kind==="text"){h=S.text_img?'<img alt="" src="/thumb/'+S.text_img+'">':'<div class="v" style="font-size:30px;white-space:pre-line">'+esc(m.text)+'</div>'}
  else if(m){const f=S.thumbs&&S.thumbs[m.kind+"/"+m.names[0]];
    h=f?'<img alt="" src="/thumb/'+f+'">':'<div class="l">your</div><div class="v" style="font-size:26px">'+(m.kind==="gif"?"animation":"picture")+'</div>'}
  else h='<div class="l">no screen chosen</div>';
  setHTML("lcd",h);
}
function renderDash(){
  $("nowshowing").textContent=modeText(S.mode);
  const r=S.readings;
  const u="<small> °"+UNIT+"</small>";
  $("s-cpu").innerHTML=temp(r.cpu)+u;$("s-vrm").innerHTML=temp(r.vrm)+u;
  $("s-liq").innerHTML=temp(r.liquid)+u;
  $("s-fan").innerHTML=(r.fan==null?"–":r.fan)+"<small> rpm</small>";$("s-pump").innerHTML=(r.pump==null?"–":r.pump)+"<small> rpm</small>";
  renderLcd();
  setHTML("lhmcard",lhmCardHtml());
}
/* ---- LibreHardwareMonitor: the Dashboard card (install button only while it can't be reached), progress, details */
let LHMLOG=null,lastInstState="idle";
function lhmIns(){return (S&&S.lhm_install)||{state:"idle",step:"",progress:null,error:"",warnings:[]}}
function lhmInstallBlock(ins){
  let h="";
  if(ins.state==="running"){
    const pct=ins.progress==null?4:Math.max(4,Math.round(ins.progress*100));
    h+='<div class="hint" style="margin:12px 0 6px">'+esc(ins.step||"Working...")+'</div><div class="bar"><i style="width:'+pct+'%"></i></div>'+
       '<div class="hint" style="margin-top:6px">If Windows asks whether this app may make changes, choose Yes. Downloading and installing takes about a minute.</div>';
  }else if(ins.state==="failed"){
    h+='<div class="hint err" style="margin:12px 0 4px"><b>That didn\'t finish.</b> '+esc(ins.error)+'</div>';
  }
  if(ins.state!=="running"&&ins.warnings&&ins.warnings.length)h+=ins.warnings.map(w=>'<div class="hint warn" style="margin:6px 0 0">'+esc(w)+'</div>').join("");
  return h;
}
function lhmLogHtml(){
  return LHMLOG?'<pre class="logbox">'+esc(LHMLOG.join("\n"))+'</pre><div class="row" style="margin-top:8px"><button class="btn" data-act="copylog">Copy details</button></div>':"";
}
function lhmCardHtml(){
  const l=S.lhm,ins=lhmIns(),busy=ins.state==="running";
  if(!l.ok&&l.checked===false)return '<span class="dot"></span>Checking for LibreHardwareMonitor...';
  if(l.ok){
    let h='<span class="dot ok"></span>LibreHardwareMonitor connected ('+l.temps.length+' temperature sensors)'+tip("lhm");
    if(S.readings.cpu==null)h+='<div class="hint warn" style="margin-top:8px">Connected, but it isn\'t reporting a CPU temperature yet. That usually means its sensor driver (PawnIO) is missing. Open Settings and press “Set up LibreHardwareMonitor for me” to fix it, or choose the sensor yourself under Settings, Temperatures.</div>'+
      (ins.warnings||[]).map(w=>'<div class="hint warn" style="margin-top:6px">'+esc(w)+'</div>').join("");
    return h;
  }
  const label=busy?"Setting up...":ins.state==="failed"?"Try again":(S.lhm_exe?"Set up LibreHardwareMonitor":"Install LibreHardwareMonitor");
  return '<span class="dot"></span><b>LibreHardwareMonitor isn\'t reachable.</b>'+tip("lhm")+
    '<div class="hint" style="margin:6px 0 12px">This app needs it to read your CPU temperature. Either it isn\'t installed, it isn\'t running, or its data feed is switched off.</div>'+
    '<div class="row" style="align-items:center"><span class="inl"><button class="btn pri'+(busy?" dis":"")+'" data-act="install">'+label+'</button>'+tip("lhminstall")+'</span>'+
    (ins.state==="failed"?'<button class="btn" data-act="log">'+(LHMLOG?"Hide details":"Show details")+'</button>':"")+'</div>'+
    lhmInstallBlock(ins)+lhmLogHtml()+
    '<div class="hint" style="margin-top:12px;font-size:11.5px;opacity:.8">Technical detail: '+esc(l.error)+'</div>';
}
function startLhmInstall(){
  if(lhmIns().state==="running")return;
  if(S)S.lhm_install=Object.assign({},lhmIns(),{state:"running",step:"Waiting for Windows' permission prompt...",progress:0,error:"",warnings:[]});
  render();act("/api/lhm/setup",{});
}
async function toggleLhmLog(){
  if(LHMLOG){LHMLOG=null;render();return}
  const r=await api("/api/lhm/log",{});
  LHMLOG=(r&&r.lines&&r.lines.length)?r.lines:["Nothing has been written down yet."];render();
}
function copyLhmLog(){
  const t=(LHMLOG||[]).join("\n");
  (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>toast("Copied."),()=>toast("Couldn't copy. Select the text and press Ctrl+C.","error"));
}
document.addEventListener("click",e=>{
  const b=e.target.closest?e.target.closest("button[data-act]"):null;if(!b)return;
  const a=b.dataset.act;
  if(a==="install")startLhmInstall();else if(a==="log")toggleLhmLog();else if(a==="copylog")copyLhmLog();
});
function curScreen(){const m=S&&S.mode;return m&&m.kind==="temp"?m.screen:null}
function setCfg(sc,patch){act("/api/screen",{screen:sc,cfg:patch})}
function renderScreens(){
  const cur=curScreen();
  if(selScreen==null&&cur!=null)selScreen=cur;
  if(cur!=null)selScreen=cur;
  if(setHTML("tiles",SCREENS.map(s=>'<div class="tile '+(cur===s[0]?"on":"")+'" data-s="'+s[0]+'"><b>'+s[1]+'</b><span>'+s[2]+'</span></div>').join("")))
    $("tiles").querySelectorAll(".tile").forEach(t=>t.onclick=()=>{selScreen=+t.dataset.s;act("/api/screen",{screen:selScreen})});
  renderOptions(cur);renderColors(cur);
}
function renderOptions(cur){
  const box=$("optcard");
  if(cur==null){setHTML("optcard",'<div class="hint">Pick a screen above first.</div>');return}
  const c=cfgOf(cur);let h='<label class="sw"><input type="checkbox" data-k="numbers" '+(c.numbers?"checked":"")+'> Show numbers on the screen'+tip("numbers")+'</label>';
  if(cur<=3){
    h+='<div style="opacity:'+(c.numbers?1:.4)+';pointer-events:'+(c.numbers?"auto":"none")+'"><label class="sw"><input type="checkbox" data-k="model" '+(c.model?"checked":"")+'> CPU model name'+(cur===1?"":' <span class="hint">(might not show)</span>')+tip("model")+'</label>'+
       '<div class="hint" style="margin:6px 0">Number to show'+tip("metric")+'</div><div class="seg">'+[["temp","CPU temperature"],["clocks","CPU clocks"],["none","None"]].map(m=>'<button data-metric="'+m[0]+'" class="'+(c.metric===m[0]?"on":"")+'">'+m[1]+'</button>').join("")+'</div></div>';
  }else if(cur===4){
    h+='<div style="opacity:'+(c.numbers?1:.4)+';pointer-events:'+(c.numbers?"auto":"none")+'"><div class="hint" style="margin:6px 0">What it shows'+tip("sens")+'</div><div class="seg">'+Object.keys(S4).map(k=>'<button data-sens="'+k+'" class="'+(k===c.sensors?"on":"")+'">'+S4[k]+'</button>').join("")+'</div>'+
       '<p class="hint" style="margin-bottom:0">One sensor fills the screen; two sensors split it in half and unlock both colors.</p></div>';
  }else if(cur===6){
    h+='<div style="opacity:'+(c.numbers?1:.4)+';pointer-events:'+(c.numbers?"auto":"none")+'"><div class="hint" style="margin:6px 0">Tick everything you want it to cycle through'+tip("items")+'</div><div class="checks">'+
       FITEMS.map(f=>'<label class="sw"><input type="checkbox" data-item="'+f[0]+'" '+(c.items.includes(f[0])?"checked":"")+'> '+f[1]+'</label>').join("")+'</div>'+
       '<div class="row" style="margin-top:6px;align-items:center"><button class="btn" data-all="1">Select all</button><button class="btn" data-all="0">Clear</button>'+
       '<span style="flex:1"></span><span class="hint">Switch to the next item about every'+tip("interval")+'</span><select data-interval="1">'+INTERVALS.map(v=>'<option value="'+v+'" '+(v===c.interval?"selected":"")+'>'+v+' seconds</option>').join("")+'</select></div></div>';
  }
  if(!setHTML("optcard",h))return;
  box.querySelectorAll("input[data-k]").forEach(i=>i.onchange=()=>setCfg(cur,{[i.dataset.k]:i.checked}));
  box.querySelectorAll("button[data-metric]").forEach(b=>b.onclick=()=>setCfg(cur,{metric:b.dataset.metric}));
  box.querySelectorAll("button[data-sens]").forEach(b=>b.onclick=()=>setCfg(cur,{sensors:b.dataset.sens}));
  box.querySelectorAll("input[data-item]").forEach(i=>i.onchange=()=>{const items=[...box.querySelectorAll("input[data-item]")].filter(x=>x.checked).map(x=>x.dataset.item);setCfg(cur,{items})});
  box.querySelectorAll("select[data-interval]").forEach(sel=>sel.onchange=()=>setCfg(cur,{interval:+sel.value}));
  box.querySelectorAll("button[data-all]").forEach(b=>b.onclick=()=>setCfg(cur,{items:b.dataset.all==="1"?FITEMS.map(f=>f[0]):[]}));
}
let colSig="";
function renderColors(cur){
  const ok=cur!=null,zones=ok?zonesOf(cur,cfgOf(cur)):[];
  $("applycol").classList.toggle("dis",!ok);
  $("z1box").style.display=zones.includes(1)||!ok?"":"none";$("z2box").style.display=zones.includes(2)||!ok?"":"none";
  const two=zones.length===2;$("z1lbl").textContent=two?"Zone 1":"Zone color";$("z2lbl").textContent=two?"Zone 2":"Zone color";
  $("colhint").textContent=ok?"":"Pick a screen first.";
  const sig=cur+"|"+JSON.stringify(S.settings.colors[cur]||0);
  if(ok&&sig!==colSig){colSig=sig;const c=S.settings.colors[cur];if(c){$("col1").value="#"+c[0];$("col2").value="#"+c[1]}}
}
$("applycol").onclick=()=>{const cur=curScreen();if(cur==null)return;const z=zonesOf(cur,cfgOf(cur));
  act("/api/colors",{screen:cur,c1:z.includes(1)?$("col1").value:null,c2:z.includes(2)?$("col2").value:null},"Colors sent.")};

function renderMedia(){
  const files=S.media[mediaTab],cur=S.mode&&S.mode.kind===mediaTab?S.mode.names:[];
  const gif=mediaTab==="gif";
  const optsHtml=gif?
   '<div class="row" style="align-items:center"><div><div class="hint">Loop length (seconds)'+tip("fill")+'</div><input type="number" id="o-fill" value="'+(window.oFill??8)+'" min="0" max="30" style="width:90px"></div>'+
   '<div><div class="hint">Max clip length (seconds)'+tip("maxclip")+'</div><input type="number" id="o-max" value="'+(window.oMax??10)+'" min="1" max="60" style="width:90px"></div>'+
   '<div class="hint" style="flex:1;min-width:220px">A short GIF is repeated inside one file up to the loop length, which hides the pause between loops. 0 = no repeat.</div></div>':
   '<div class="row" style="align-items:center"><div><div class="hint">Picture fit'+tip("fit")+'</div><div class="seg" id="o-fit"><button data-f="crop" class="on">Crop to fill</button><button data-f="pad">Fit with black bars</button></div></div></div>';
  const fresh=setHTML("mopts",optsHtml);
  if(fresh){if(!gif)$("o-fit").querySelectorAll("button").forEach(b=>b.onclick=()=>{window.oFit=b.dataset.f;$("o-fit").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b))});
  if(!gif&&window.oFit)$("o-fit").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x.dataset.f===window.oFit));
  if(gif){$("o-fill").onchange=e=>window.oFill=e.target.value;$("o-max").onchange=e=>window.oMax=e.target.value}}
  const listHtml=files.length?files.map((n,i)=>'<div class="item '+(cur.includes(n)?"on":"")+'">'+(S.thumbs&&S.thumbs[mediaTab+"/"+n]?'<img class="thumb" alt="" src="/thumb/'+S.thumbs[mediaTab+"/"+n]+'">':"")+'<span class="nm">'+esc(n)+'</span>'+
    '<button class="btn" data-a="play" data-n="'+esc(n)+'">Play</button><button class="btn bad" data-a="del" data-n="'+esc(n)+'">Delete</button></div>').join(""):
    '<div class="hint">Nothing listed yet. Press “Load list from cooler”. (Loading briefly switches the screen.)</div>';
  if(setHTML("mlist",listHtml))$("mlist").querySelectorAll("button").forEach(b=>b.onclick=()=>{
    if(b.dataset.a==="play")act("/api/media/play",{what:mediaTab,names:[b.dataset.n]});
    else if(confirm("Permanently delete '"+b.dataset.n+"' from the cooler?"))act("/api/media/delete",{what:mediaTab,name:b.dataset.n});
  });
}
document.querySelectorAll("#mseg button").forEach(b=>b.onclick=()=>{mediaTab=b.dataset.w;document.querySelectorAll("#mseg button").forEach(x=>x.classList.toggle("on",x===b));renderMedia()});
$("mrefresh").onclick=()=>act("/api/media/refresh",{what:mediaTab});
$("mpick").onclick=()=>{$("mfile").accept=mediaTab==="gif"?".gif,.mp4,.mov,.webm,.mkv,.avi,.webp,image/gif,video/*":"image/*";$("mfile").value="";$("mfile").click()};
$("mfile").onchange=async()=>{
  const f=$("mfile").files[0];if(!f)return;
  const opts=mediaTab==="gif"?{fill:+($("o-fill").value||0),max_seconds:+($("o-max").value||10)}:{fit:window.oFit||"crop"};
  busyUpload=true;$("mprog").style.display="block";$("mproglabel").textContent="Sending "+f.name+" to the app...";$("mprogbar").style.width="2%";
  try{
    const r=await fetch("/api/upload",{method:"POST",headers:{"X-Token":TOKEN,"X-What":mediaTab,"X-Filename":btoa(unescape(encodeURIComponent(f.name))),"X-Opts":JSON.stringify(opts)},body:f});
    const j=await r.json();if(j.ok===false)toast(j.error,"error");
  }catch(e){toast("Upload failed: "+e,"error")}
  busyUpload=false;
};
let textInit=false,prevTimer=null,prevSeq=0;
const PADX=[-70,0,70],PADY=[-80,0,80];
$("t-pad").innerHTML=[0,1,2].map(r=>[0,1,2].map(c=>'<button data-x="'+PADX[c]+'" data-y="'+PADY[r]+'">•</button>').join("")).join("");
function tStyle(){return {color:$("t-color").value.slice(1),bg:$("t-bg").value.slice(1),font:$("t-font").value,size:+$("t-size").value,x:+$("t-x").value,y:+$("t-y").value,slant:+$("t-slant").value,rotate:+$("t-rot").value}}
function tLabels(){$("t-sizev").textContent=$("t-size").value;$("t-xv").textContent=$("t-x").value;$("t-yv").textContent=$("t-y").value;$("t-sv").textContent=$("t-slant").value;$("t-rv").textContent=$("t-rot").value;
  document.querySelectorAll("#t-pad button").forEach(b=>b.classList.toggle("on",+b.dataset.x===+$("t-x").value&&+b.dataset.y===+$("t-y").value))}
function tPreview(){tLabels();clearTimeout(prevTimer);prevTimer=setTimeout(async()=>{const my=++prevSeq;
  const r=await api("/api/text/preview",{text:$("txt").value||"HELLO",style:tStyle()});if(my===prevSeq&&r&&r.png)$("t-prev").src="data:image/png;base64,"+r.png},180)}
["t-color","t-bg","t-font","t-size","t-x","t-y","t-slant","t-rot"].forEach(id=>$(id).oninput=tPreview);
$("txt").oninput=tPreview;
document.querySelectorAll("#t-pad button").forEach(b=>b.onclick=()=>{$("t-x").value=b.dataset.x;$("t-y").value=b.dataset.y;tPreview()});
$("t-reset").onclick=()=>{$("t-x").value=0;$("t-y").value=0;$("t-slant").value=0;$("t-rot").value=0;tPreview()};
$("txtsend").onclick=()=>act("/api/text",{text:$("txt").value,style:tStyle()},"Sending text...");
let fontSig="";
function renderFonts(){const fonts=S.fonts||[],sig=fonts.join("|");
  if(sig!==fontSig){fontSig=sig;const sel=$("t-font"),cur=sel.value;
    sel.querySelectorAll("optgroup").forEach(g=>g.remove());
    if(fonts.length){const g=document.createElement("optgroup");g.label="Your fonts";
      fonts.forEach(f=>{const o=document.createElement("option");o.value="file:"+f;o.textContent=f.replace(/\.[^.]+$/,"");g.appendChild(o)});sel.appendChild(g)}
    sel.value=cur;if(sel.value!==cur){sel.value="arial";if(textInit)tPreview()}}
  $("font-del").style.display=$("t-font").value.startsWith("file:")?"":"none"}
$("t-font").addEventListener("change",()=>{$("font-del").style.display=$("t-font").value.startsWith("file:")?"":"none"});
$("font-add").onclick=()=>{$("font-file").value="";$("font-file").click()};
$("font-file").onchange=async()=>{const f=$("font-file").files[0];if(!f)return;
  try{const r=await fetch("/api/font",{method:"POST",headers:{"X-Token":TOKEN,"X-Filename":encodeURIComponent(f.name)},body:f});const j=await r.json();
    if(j.ok===false)toast(j.error,"error");else{toast("Font added.");const st=await api("/api/state");if(st&&st.settings){S=st;renderFonts();$("t-font").value=j.font;tPreview();$("font-del").style.display=""}}}
  catch(e){toast("Upload failed: "+e,"error")}};
$("font-del").onclick=async()=>{const v=$("t-font").value;if(!v.startsWith("file:"))return;
  if(!confirm("Remove the font '"+v.slice(5)+"'?"))return;await act("/api/font/remove",{name:v.slice(5)},"Font removed.");$("t-font").value="arial";tPreview()};
function initText(){if(textInit||!S)return;renderFonts();textInit=true;const t=S.settings.text||{};
  $("txt").value=t.text||"HELLO";$("t-color").value="#"+(t.color||"ffffff");$("t-bg").value="#"+(t.bg||"000000");$("t-font").value=t.font||"arial";
  $("t-size").value=t.size||56;$("t-x").value=t.x||0;$("t-y").value=t.y||0;$("t-slant").value=t.slant||0;$("t-rot").value=t.rotate||0;tPreview()}

const ACC=["#ff6a1a","#ffb000","#3ddc84","#18c8ff","#5b7cff","#b36bff","#ff4f9a","#ff4d4d"];
const BGS=[["#0d0f14","Dark"],["#0b1020","Midnight"],["#17181c","Charcoal"],["#0c1411","Forest"],["#150f1a","Plum"],["#f0f2f6","Light"]];
$("th-acc-sw").innerHTML=ACC.map(c=>'<button class="sw2" data-c="'+c+'" style="background:'+c+'" title="'+c+'"></button>').join("");
$("th-bg-sw").innerHTML=BGS.map(c=>'<button class="sw2" data-c="'+c[0]+'" style="background:'+c[0]+'" title="'+c[1]+'"></button>').join("");
let theme=Object.assign({},THEME0),themeTimer=null;
function setTheme(patch){theme=Object.assign(theme,patch);applyTheme(theme);$("th-accent").value=theme.accent;$("th-bg").value=theme.bg;
  clearTimeout(themeTimer);themeTimer=setTimeout(()=>api("/api/settings",{theme}),400)}
$("th-accent").value=theme.accent;$("th-bg").value=theme.bg;
$("th-accent").oninput=e=>setTheme({accent:e.target.value});$("th-bg").oninput=e=>setTheme({bg:e.target.value});
$("th-acc-sw").querySelectorAll("button").forEach(b=>b.onclick=()=>setTheme({accent:b.dataset.c}));
$("th-bg-sw").querySelectorAll("button").forEach(b=>b.onclick=()=>setTheme({bg:b.dataset.c}));
$("th-reset").onclick=()=>setTheme({accent:"#ff6a1a",bg:"#0d0f14"});
let logoVer=-1;
function renderLogo(){const v=(S.settings.logo_version||0)+"|"+(S.custom_logo?1:0);if(v===logoVer)return;logoVer=v;
  const url="/logo.png?v="+encodeURIComponent(v);
  $("brandimg").src=url;$("logoprev").src=url;
  document.querySelectorAll("link[rel=icon]").forEach(l=>{l.href="/icon/"+l.dataset.n+".png?v="+encodeURIComponent(v)});
  $("nologo").textContent=S.custom_logo?"Using your own logo.":"Using the built-in Waterforce logo.";
  $("logo-del").style.display=S.custom_logo?"":"none"}
$("logo-pick").onclick=()=>{$("logo-file").value="";$("logo-file").click()};
$("logo-file").onchange=async()=>{const f=$("logo-file").files[0];if(!f)return;
  try{const r=await fetch("/api/logo",{method:"POST",headers:{"X-Token":TOKEN},body:f});const j=await r.json();if(j.ok===false)toast(j.error,"error");else toast("Logo updated.")}catch(e){toast("Upload failed: "+e,"error")}};
$("logo-del").onclick=()=>act("/api/logo/remove",{},"Back to the built-in logo.");
function sensorOpts(sel,cur,kind){
  const el=$(sel);if(document.activeElement===el)return;
  const opts=['<option value="">Automatic</option>'].concat(S.lhm.temps.map(t=>'<option value="'+esc(t[0])+'">'+esc(t[1])+' — '+(Math.round(cvt(t[2])*10)/10)+'°'+UNIT+' ('+esc(t[0])+')</option>'));
  const sig=opts.length+"|"+cur+"|"+UNIT;if(el.dataset.sig===sig)return;el.dataset.sig=sig;
  el.innerHTML=opts.join("");el.value=cur||"";if(cur&&el.value!==cur){el.insertAdjacentHTML("beforeend",'<option selected value="'+esc(cur)+'">'+esc(cur)+'</option>')}
}
async function loadSystem(){SYS=await api("/api/system");renderSettings()}
function renderSettings(){
  if(!S)return;const st=S.settings;
  if(document.activeElement!==$("set-lhmpath"))$("set-lhmpath").value=st.lhm_path;
  $("set-launch").checked=st.launch_lhm;$("set-apply").checked=st.apply_on_start;
  sensorOpts("set-cpu",st.cpu_sensor_id);sensorOpts("set-vrm",st.vrm_sensor_id);
  if(SYS){
    $("set-auto").checked=!!SYS.autostart;
    const h=$("autohint");if(!SYS.windows){h.style.display="block";h.textContent="Start-with-Windows only works on Windows."}else h.style.display="none";
    $("lhmtaskhint").textContent=SYS.lhm_task?"✔ It will start by itself, as administrator, every time you log in.":"Automatic start isn't set up yet - the button above does it (Windows asks for permission once).";
  }
  const ins=lhmIns();
  $("lhm-setup").classList.toggle("dis",ins.state==="running");
  setHTML("lhmstatus",(S.lhm.ok?'<span class="dot ok"></span>Running and sending temperatures':'<span class="dot"></span>Not sending temperatures yet')+
    '<div class="hint">'+(S.lhm_exe?"Found at "+esc(S.lhm_exe):"Not installed yet")+'</div>'+
    (SYS&&SYS.windows&&(SYS.pawnio||S.readings.cpu==null)?'<div class="hint">Sensor driver (PawnIO): '+(SYS.pawnio?"installed":"not installed - the setup button installs it")+'</div>':""));
  setHTML("lhminst",lhmInstallBlock(ins)+(ins.state==="failed"?'<div class="row" style="margin-top:8px"><button class="btn" data-act="log">'+(LHMLOG?"Hide details":"Show details")+'</button></div>':"")+lhmLogHtml());
}
$("set-auto").onchange=async e=>{await act("/api/autostart",{on:e.target.checked});loadSystem()};
$("set-launch").onchange=e=>act("/api/settings",{launch_lhm:e.target.checked});
$("set-apply").onchange=e=>act("/api/settings",{apply_on_start:e.target.checked});
$("save-lhm").onclick=()=>act("/api/settings",{lhm_path:$("set-lhmpath").value.trim().replace(/^"|"$/g,"")},"Saved.");
$("set-cpu").onchange=e=>act("/api/settings",{cpu_sensor_id:e.target.value},"CPU sensor saved.");
$("set-vrm").onchange=e=>act("/api/settings",{vrm_sensor_id:e.target.value},"VRM sensor saved.");
$("lhm-setup").onclick=startLhmInstall;
$("lhmtask-off").onclick=async()=>{await act("/api/lhm/task",{on:false},"Approve Windows' permission prompt to turn it off.");setTimeout(loadSystem,15000)};
$("quit").onclick=()=>{if(confirm("Quit the app? The cooler will stop getting temperatures."))api("/api/quit",{})};

function renderStatus(){
  $("cdot").className="dot"+(S.connected?" ok":"");
  $("ctext").textContent=S.connected?"Cooler connected":"Cooler not found";
  const b=$("banner");
  if(!S.connected){b.style.display="block";b.textContent=S.cooler_error||"Looking for the cooler...";}
  else if(S.busy){b.style.display="block";b.textContent=S.busy.label+(S.busy.progress!=null?"  "+Math.round(S.busy.progress*100)+"%":"...");}
  else b.style.display="none";
  if(S.busy&&S.busy.progress!=null){$("mprog").style.display="block";$("mproglabel").textContent=S.busy.label;$("mprogbar").style.width=Math.round(S.busy.progress*100)+"%"}
  else if(S.busy&&/^Converting/.test(S.busy.label)){$("mprog").style.display="block";$("mproglabel").textContent=S.busy.label;$("mprogbar").style.width="100%"}
  else if(!busyUpload)$("mprog").style.display="none";
  for(const e of S.events){if(e.id>seenEv){seenEv=e.id;if(!firstState)toast(e.text,e.level)}}
  firstState=false;
}
function render(){
  if(!S)return;
  const is=lhmIns().state;if(lastInstState==="running"&&is!=="running")loadSystem();lastInstState=is;
  if(Date.now()>unitLock){UNIT=S.settings.unit==="F"?"F":"C"}renderUnit();
  renderStatus();renderLogo();initText();renderFonts();
  if(curPage==="dash")renderDash();else if(curPage==="screens")renderScreens();
  else if(curPage==="media"&&!document.activeElement.matches("input"))renderMedia();else if(curPage==="settings")renderSettings();
}
async function poll(){const s=await api("/api/state");if(s&&s.settings){S=s;render()}else if(S==null){}
  setTimeout(poll,1000)}
poll();
</script></body></html>
"""
