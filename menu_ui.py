"""메뉴의 공통 글꼴·여백·선택 표시·키 안내."""

import pico2d
from ui_text import UIFont
from controls_view import keycap,fonts as control_fonts
from effects import blended

TEXT=(225,233,238)
MUTED=(170,188,201)
GOLD=(240,207,143)
GREEN=(154,216,182)
RED=(234,154,137)
EDGE=(62,79,94)
_body=None


def body_font():
    global _body
    if _body is None:_body=UIFont(16)
    return _body


def clear_resources():
    global _body
    if _body is not None:_body.close()
    _body=None


def header(heading,title,subtitle='',balance=None):
    heading.draw(52,486,title,GOLD)
    body_font().draw(52,448,subtitle,MUTED)
    if balance is not None:
        body_font().draw(744,485,f'전력 조각  {balance}',GOLD)
    pico2d.draw_line(52,424,908,424,*EDGE)


def panel(left,bottom,right,top,selected=False,enabled=True):
    pico2d.draw_rectangle(left,bottom,right,top,20,31,43,filled=True)
    pico2d.draw_rectangle(left,bottom,right,top,*(GOLD if selected else EDGE))
    if selected:pico2d.draw_rectangle(left,bottom,left+3,top,*GOLD,filled=True)


def footer(entries,y=48):
    small,key_font=control_fonts()
    pico2d.draw_rectangle(0,0,959,y+36,8,15,24,filled=True)
    pico2d.draw_line(52,y+30,908,y+30,*EDGE)
    for x,key,label in entries:keycap(key,label,x,y,small,key_font)


def selection_row(font,text,x,y,width,selected=False):
    if selected:
        pico2d.draw_rectangle(x-15,y-23,x+width,y+23,32,43,53,filled=True)
        pico2d.draw_rectangle(x-15,y-23,x-12,y+23,*GOLD,filled=True)
    font.draw(x,y,text,GOLD if selected else TEXT)


def choice_overlay(heading,title,items,selection,subtitle='',warning='',escape_label='계속하기'):
    with blended():
        pico2d.draw_rectangle(0,0,959,539,5,11,19,a=218,filled=True)
    panel(236,96,724,452)
    heading.draw(274,413,title,GOLD)
    body_font().draw(274,373,subtitle,MUTED)
    pico2d.draw_line(274,350,686,350,*EDGE)
    for i,label in enumerate(items):
        selection_row(body_font(),label,289,313-i*52,375,i==selection)
    if warning:body_font().draw(274,114,warning,RED)
    footer(((236,'↑ ↓','선택'),(430,'E','확인'),(606,'ESC',escape_label)))
