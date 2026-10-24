"""Proportion check by eye: his photo | the model | the model laid over the photo (red), same fitted camera, with a grid. Not a target: a way to see proportions. usage: python tools/parts_overlay.py MODEL_DIR OUT.png master,s03,s09 (run tools/parts_sheet.py on MODEL_DIR first)"""
import sys
from PIL import Image, ImageDraw
V={"master":"references/master/master_front_standing.webp","s02":"references/sheet_originals/02_front_3q.webp","s03":"references/sheet_originals/03_right_profile.webp","s04":"references/sheet_originals/04_back_3q_right.webp","s07":"references/sheet_originals/07_left_profile.webp","s08":"references/sheet_originals/08_front_3q_left.webp","s09":"references/sheet_originals/09_top_down.webp"}
d=sys.argv[1]; out=sys.argv[2]; views=sys.argv[3].split(',')
rows=[]
for n in views:
    a=Image.open(V[n]).convert('RGB'); b=Image.open(f'{d}/ps_{n}.png').convert('RGBA')
    bg=Image.new('RGBA',b.size,(228,228,228,255)); bg.alpha_composite(b); b=bg.convert('RGB')
    m=b.split()[0].point(lambda v:0); al=Image.open(f'{d}/ps_{n}.png').split()[3]
    tint=Image.new('RGB',a.size,(255,60,60)); ov=Image.composite(Image.blend(a,tint,0.45),a,al)
    W,H=a.size; o=Image.new('RGB',(3*W,H),'white')
    for i,im in enumerate((a,b,ov)): o.paste(im,(i*W,0))
    g=ImageDraw.Draw(o)
    for k in range(1,20):
        y=H*k//20; g.line([(0,y),(3*W,y)],fill=(255,0,0) if k%5==0 else (255,190,190),width=2)
    o.thumbnail((1800,800)); rows.append(o)
O=Image.new('RGB',(max(r.width for r in rows),sum(r.height+6 for r in rows)),'white'); y=0
for r in rows: O.paste(r,(0,y)); y+=r.height+6
O.save(out)
