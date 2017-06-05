# $Id: readcab.py,v 1.17 2017-02-21 02:36:14 eikii Exp $

import subprocess
import sys
import re

import data as d
DBG_READCAB = True
DBG_SKIPCAB = True

#### コマンド引数で与えたファイル名をcabochaで読む

if DBG_SKIPCAB:
  Cab_cmd = "cat"   # for dbg
  Cab_opt = ""
else:
  Cab_cmd = "/Users/eikii/eilocal/bin/cabocha"   # for dbg, use "cat"
  Cab_opt = "-O3"

def cab_init():
  global p, rchk, rtok
  file = sys.argv[1]
  args = [ Cab_cmd, Cab_opt, file ]
  p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  rchk = re.compile(' (\d+) -1D (\d+)/(\d+) ')
  rtok = re.compile(
r'([^,\s]+)\s([^,\s]+),([^,\s]+),([^,\s]+),([^,\s]+),([^,\s]+),([^,\s]+),([^,\s]+)(,([^,\s]+))?(,([^,\s]+))?\s')
     #r'(\S+)\s(\S+),(\S+),(\S+),(\S+),(\S+),(\S+),(\S+),(\S+),(\S+)\s')
     # '/','q'はカナと発音がないので8,9thを省略したいが、
     #\Sだと最初(pos1)がコンマにマッチしてpos1-3を含んでしまう

#### 1文を読み込み、文節分割までの結果をd.cabchunkに入れる
#    一度の呼び出しごとに、EOSまで読み込む

def cab_do_a_sentence():
  global p, rchk, rtok
  tokens = []
  chunks = []
  lastchunk  = tokentop = tokencnt = 0
  chunk = d.CabChunk()
  chunk.token_pos = 0
  
  ## cabocha出力を１行ずつ処理。cabocha出力例：
  
  #* 0 -1D 0/0 0.000000 F_H0:この,F_H1:連体詞,F_F0:この,...
  #この    連体詞,*,*,*,*,*,この,コノ,コノ O
  #* 1 -1D 0/0 0.000000 F_H0:先,F_H1:名詞,F_H2:一般,F_F0:先,...
  #先      名詞,一般,*,*,*,*,先,サキ,サキ  O
  #* 2 -1D 1/1 0.000000 F_H0:のこる,F_H1:動詞,F_H2:自立,...
  #生き    動詞,自立,*,*,一段,連用形,生きる,イキ,イキ      O
  #のこる  動詞,自立,*,*,五段・ラ行,基本形,のこる,ノコル,ノコル    O
  
  line_read = False
  for lnb in p.stdout:
    line_read = True
    ln  = lnb.decode('utf-8')  ## stdoutから読んだ行はbytes(!str)なので注意
    #print("===={}$$$$".format(ln))  ####
    m = rchk.search(ln)
    if m is not None:
        chunknum = m.group(1)
        #print("---- chunk:{}/{}/{}/{} ----".format(
        #              chunk.token_pos,tokencnt,chunk.head_pos,chunk.func_pos))
        if lastchunk != 0:
            chunk.token_size = tokencnt
            chunks.append(chunk)
            chunk = d.CabChunk()
            chunk.token_pos = tokentop
            tokencnt = 0
        chunk.head_pos = int(m.group(2))
        chunk.func_pos = int(m.group(3))
        lastchunk += 1
    else:
        m = rtok.search(ln)
        if m is not None:
            tok = d.Token()
            tok.surface = m.group(1)
            tok.pos1 = m.group(2)
            tok.pos2 = m.group(3)
            tok.pos3 = m.group(4)
            tok.pos4 = m.group(5)
            tok.cjtype = m.group(6)
            tok.cjform = m.group(7)
            tok.baseform = m.group(8)
            tok.kana = m.group(9)
            tok.pronou = m.group(10)
            tokens.append(tok)
            tokentop += 1
            tokencnt += 1
            #print("---- token:{}/{}/{} ----".format(
            #              tok.pos1,tok.pos2,tok.pronou))
        else:
            print("---- not chunk nor token ----")
  
    if re.match(r'^EOS', ln):  ## EOSがあったらそこまでの１文を処理
      chunk.token_size = tokencnt
      chunks.append(chunk)
      if DBG_READCAB:
        print("---- Tokens ----")
        for t in tokens:
          print(" {}/{}/{}/{}/{}/{}/{}/{}/{}/{}".format(t.surface,
             t.pos1, t.pos2, t.pos3, t.pos4, t.cjtype, t.cjform,
             t.baseform, t.kana, t.pronou
          ))
        print("---- Chunks ----")
        for c in chunks:
          print(" {}/{}/{}/{}".format(
              c.token_pos, c.token_size, c.head_pos, c.func_pos
          ))
      d.cabchunks = chunks
      d.cabtokens = tokens
      return

  if not line_read:
    exit()
