"""Apply the Soulu presentation to the private pinned installer checkout."""
from pathlib import Path
import shutil,sys
root=Path(__file__).resolve().parents[2]
core=Path(sys.argv[1]);payload=Path(sys.argv[2]).resolve()
web=core/'core/web';fonts=payload/'engine/soulu/chrome/ui/fonts'
for name in ['Inter.ttf','Inter-OFL.txt']:shutil.copyfile(fonts/name,web/'assets'/name)
for name in ['Montserrat.ttf','Montserrat-OFL.txt']:(web/'assets'/name).unlink(missing_ok=True)
style=web/'style.css'
style.write_text(style.read_text(encoding='utf-8').replace("Montserrat.ttf","Inter.ttf").replace("Montserrat","Inter"),encoding='utf-8')
shutil.copyfile(root/'gecko/installer/soulu-theme.css',web/'soulu-theme.css')
index=web/'index.html';source=index.read_text(encoding='utf-8')
source=source.replace('</head>','<link rel="stylesheet" href="soulu-theme.css"></head>')
for name,old,view,path in [('minimize','−','0 0 24 24','M4.5 12h15'),('close','×','0 0 16 16','m4 4 8 8m0-8-8 8')]:
    before=('aria-label="Свернуть">'+old+'</button>') if name=='minimize' else ('aria-label="Закрыть">'+old+'</button>')
    assert before in source,name
    source=source.replace(before,before.split('>')[0]+'><svg viewBox="'+view+'" aria-hidden="true"><path d="'+path+'"/></svg></button>')
index.write_text(source,encoding='utf-8')
