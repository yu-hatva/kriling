# $Id: main.py,v 1.19 2017-02-21 07:40:24 eikii Exp $

import pickle

import data as d
import readcab
import blddep
import srch

DBG_MAIN = True
def dpr(msg):
  d.dbgprint(DBG_MAIN, msg)

d.obj_stack = []
d.pred_stack = []
prev_qa_req = False
d.odict = pickle.load(open("compiled_dic.pkl", "rb"))
dpr("dict load done")

readcab.cab_init()
dpr("@@@@MAIN cab_init done")
d.sent_cnt = 0
while True:
  dpr("@@@@MAIN start a sent")
  d.sent_cnt += 1
  readcab.cab_do_a_sentence()
  dpr("@@@@MAIN cab_sent done")
  if d.cabtokens[0].surface == '/' and d.cabtokens[1].surface == 'q':
      prev_qa_req = True  # '/q'なら 1)この文は解析しない 2)次の文は質問と解釈
      continue
  blddep.builddep()
  dpr("@@@@MAIN blddep done")
  srch.depsrch_root()
  dpr("@@@@MAIN depsrch done")
  srch.pawssrch_heap()
  dpr("@@@@MAIN pawssrch done")
  if prev_qa_req:  # 直前が'/q'のケース。文法解析のみ。obj/predはいじらない
      srch.do_qa()
      dpr("@@@@MAIN qa done")
      prev_qa_req = False
  else:
      srch.anasrch_heap()
      dpr("@@@@MAIN anasrch done")
