# $Id: blddep.py,v 1.32 2017-02-21 06:50:06 eikii Exp $

import data as d
import defdict as dd
from defdict import DepLbl
import enum

DBG_BLD = False
def dpr(msg):
  d.dbgprint(DBG_BLD, msg)

def expand():
    """
    暗黙の入力：d.cabchunks 　　　：CabChunkのリスト
    暗黙の出力：d.cabchunks_exped ：CabChunkのリスト
    「〜のような気がする」のように、cabochaでは複数文節になるが
    oolongとしては一文節として扱いたいようなケースで、
    「伸ばした」文節を作って返す。伸ばすのに使用したモダリティのみセットする
    """
    # FIXME TBC  とりあえず、伸ばすケースがない文のみ扱うとする
    d.cabchunks_exped = d.cabchunks

    sz = len(d.cabchunks_exped)
    d.chunks = []
    for i in range(sz): # 各（伸ばした）文節についてループ
        ch = dd.Chunk()
        ch.chsuf = i
        ch.cab = d.cabchunks_exped[i]  # i番目のcabocha展開文節
        d.chunks.append(ch)  # chunksにまっさらな文節を追加

#### extract_features()と、そこで使う関数たち

FuncType = enum.Enum("FuncType", [   # FIXME? これもdata.pyへ?
  "INVALID",
  "ADNOM",        # 連体詞
  "ADV",          # 副詞
  "CJADNOM",      # 連体形
  "ADJRENYOU",    # 形容詞連用形
  "VXRENYOU",     # 動詞・助動詞連用形
  "CJTERM",       # 終止形
  "NOUN",         # 名詞
  "ADVNOUN",      # 副詞可能名詞
  "NOUNCOMMA",    # 名詞＋コンマ
  "CONJFWD",      # 接続詞順接
  "CONJREV",      # 接続詞逆接
  "INTERJ",       # 感動詞
  "PPCASE",       # 格助詞
  "PPKAKAFUK",    # 係・副助詞
  "PPCONJFWD",    # 接続助詞順接
  "PPCONJREV",    # 接続助詞逆接
  "PPCONJADV",    # 接続助詞副詞節
  "PPTERM",       # 終助詞
  "PPPARA",       # 並立助詞
  "PPTARI",       # 並立助詞タリ・ダリ
  "PPADVIZE",     # 副詞化
  "PPADNOMIZE",   # 連体化
  "NONE"
])

MainType = d.MainType  # 定義をdata.pyへ移動


def set_chunk_modality(ch):
    """
    Cab文節cabにあるモダリティ（文末）表現を見て、各フラグを文節chにセット。
    chには既に(expand()がセットした)フラグがいくつかあるので、足し込む
    """
    ntok = len(d.cabtokens)
    cab = ch.cab
    # FIXME expandで既存のものには触らない
    ch.has_aux_da = False
    ch.has_topic_HA = False
    ch.has_comma_last = False
    ch.ppcase = ""
    ch.voice_causative = False
    ch.voice_passive = False
    ch.named_entity = False
    ch.pronoun_animate = False
    ch.pronoun_male = False
    ch.pronoun_female = False
    ch.pronoun_interrogative = False
    ch.tense_past = False
    ch.aspect_TEIRU = False
    ch.has_ppconj_KARA = False
    ch.has_ppterm_KA = False

    # 全てのトークンを見る

    for i in range(cab.token_pos, cab.token_pos+cab.token_size):
        tok = d.cabtokens[i]
        tok2 = d.cabtokens[i+1] if i+1 < ntok else None
        if tok.pos1 == "助動詞":
            if tok.cjtype in [ "特殊・ダ" , "特殊・デス" ]:
                ch.has_aux_da = True    # 判定詞あり
            elif tok.cjtype == "特殊・タ":
                ch.tense_past = True    # テンス＝過去
        elif tok.pos1 == "助詞":
            if tok.pos2 == "係助詞":
                if tok.surface == "は":
                    ch.has_topic_HA = True    # topic ハ
            elif tok.pos2 == "格助詞":
                ch.ppcase = tok.surface
            elif tok.pos2 == "接続助詞":
                if tok.surface == "て" and tok2 and tok2.pos1 == "動詞" and \
                   tok2.pos2 == "非自立" and tok2.baseform == "いる":
                    ch.aspect_TEIRU = True
                elif tok.surface == "から":
                    ch.has_ppconj_KARA = True
            elif tok.pos2 == "副助詞／並立助詞／終助詞":
                    ch.has_ppterm_KA = True
        elif tok.pos1 == "動詞":
            if tok.pos2 == "接尾" and tok.baseform in ["れる", "られる"]:
                ch.voice_passive = True
            if tok.pos2 == "接尾" and tok.baseform in ["せる", "させる"]:
                ch.voice_causative = True
        # TBC more...

    # 主辞トークンのみ見る
    #tok = maintok(ch)
    #tok = d.cabtokens[cab.token_pos+cab.head_pos]  - mainposまだ設定してない！
    tok = d.cabtokens[cab.token_pos] # FIXME!!! temp patch とりあえず最初と仮定
    if tok.pos1 == "名詞":
        if tok.pos2 == "固有名詞":
            ch.named_entity = True
        elif tok.pos2 == "代名詞":
            if tok.surface == "彼":
                ch.pronoun_animate = True
                ch.pronoun_male = True
            elif tok.surface == "彼女":
                ch.pronoun_animate = True
                ch.pronoun_female = True
            elif tok.surface == "誰":
                ch.pronoun_interrogative = True
            elif tok.surface == "何":
                ch.pronoun_interrogative = True

    # 最後のトークンのみ見る
    tok = d.cabtokens[cab.token_pos+cab.token_size-1]
    if tok.surface == "、":
        ch.has_comma_last = True    # 文節の最後がコンマ
    # TBC more...

def functyp(ch):
    """ 文節を受け取り、その機能辞のタイプを返す """
    tokf = d.cabtokens[ch.cab.token_pos+ch.cab.func_pos] # 文節の機能辞トークン
    pos01 = tokf.pos1
    pos02 = tokf.pos2
    # FIXME TBC; depbuild.cc functyp()からコピー
    if pos01 == "連体詞":
        return FuncType.ADNOM
    elif pos01 == "動詞":
        return FuncType.CJTERM
    elif pos01 == "助詞":
        if pos02 == "格助詞":
            return FuncType.PPCASE
        elif pos02 == "係助詞" or pos02 == "副助詞":
            return FuncType.PPKAKAFUK


def maintok(ch):
    """ 文節を受け取り、その主辞のトークンを返す """
    return d.cabtokens[ch.cab.token_pos+ch.cab.head_pos]  # 文節の主辞トークン

def maintyp(ch):
    """ 文節を受け取り、その主辞のタイプを返す """
    tokm = maintok(ch)  # この文節の主辞のトークン
    # FIXME findMainWord()にする？
    pos01 = tokm.pos1
    pos02 = tokm.pos2
    # FIXME TBC; depbuild.cc maintyp()からコピー
    if pos01 == "連体詞":
        return MainType.ADNOM
    elif pos01 == "動詞":
        return MainType.VERB
        # NOTE cabochaでは、サ変名詞＋スルだとスルがmainになる。
        # FIXME findMainWord()にしたらここ変わるかも？注意！
    elif pos01 == "名詞":
        if pos02 == "形容動詞語幹" and ch.has_aux_da:
            return MainType.ADJ         # 形容動詞
        elif ch.has_aux_da:
            return MainType.NOUNDAPRED  # 名詞＋ダ
        else:
            return MainType.NOUN        # 名詞


def extract_features():
    """
    1) expand()で扱わないモダリティをセット
    2) 主辞、機能辞のタイプを判別
    """
    sz = len(d.cabchunks_exped)
    for i in range(sz): # 各（伸ばした）文節についてループ
        ch = d.chunks[i]

        # 1)モダリティのセット
        set_chunk_modality(ch)

        # 2)主辞、機能辞  *ch.has_aux_da等を使うので1)の後で
        ch.maintyp = maintyp(ch)
        ch.functyp = functyp(ch)

        # :


#    3) chunk_relation_tbl　をセット（係ったときの、文節間の関係）

def set_chunk_relations():
    n = len(d.chunks)
    # 以下ではダメ：各行が同じobjになる
    #d.chunk_relation_tbl = [ [DepLbl.INVALID] * n ] * (n-1)
    d.chunk_relation_tbl = [ ([DepLbl.INVALID] * n) for i in range(n-1) ]
    for i in range(n-1):
        srcfunc = d.chunks[i].functyp
        for j in range(i+1,n):         # 文節i->jの係り
            dstmain = d.chunks[j].maintyp
            lbl = DepLbl.INVALID
            if   srcfunc == FuncType.PPCASE and dstmain == MainType.VERB:
                lbl = DepLbl.CASECOMP
            elif srcfunc == FuncType.PPKAKAFUK and dstmain == MainType.VERB:
                lbl = DepLbl.CASECOMP
            # FIXME TBC more...
            d.chunk_relation_tbl[i][j] = lbl

#    4) dep_eval_tblをセット（係りの評価点）

# FIXME bogus - tune later
dist_cost_tab = [ 0, 0, 3, 5, 7, 10, 13, 17 ]
dist_cost_tab.extend([17] * 40)
#print(dist_cost_tab)  ####
IMMEDIATE_CROSSCOMMA_COST = 20
BAD_DEP_COST = 999

def set_dep_eval_tab():
    global dist_cost_tab
    n = len(d.chunks)
    d.dep_eval_tbl = [ ([-BAD_DEP_COST] * n) for i in range(n-1) ]
    for i in range(n-1):
        for j in range(i+1,n):       # 文節i->jの係り
            if d.chunk_relation_tbl[i][j] == DepLbl.INVALID:
                continue        # 係り得ないならスキップ(-BAD_DEP_COSTが残る)
            point = - dist_cost_tab[j-i]  # 文節距離による点
            if d.chunks[i].has_comma_last and j==i+1:
                point -= IMMEDIATE_CROSSCOMMA_COST #コンマをまたいで直後には係らない
            # FIXME TBC more...
            # topicハ＋連体節、はdepsrch()の中でやる（二つの係りが必要なため）
            d.dep_eval_tbl[i][j] = point
            dpr(":: in set_eval i:{} j:{} pt:{}".format(i,j,point))

# 辞書エントリをセット

def get_dictent():
    n = len(d.chunks)
    for i in range(n):
        tokm = maintok(d.chunks[i])
        if tokm.pos1 not in ["名詞", "動詞", "形容詞", "副詞"]:
            continue    # FIXME 連体詞は？
        dic_idx = tokm.surface if tokm.pos1 in ["名詞", "副詞"] \
                               else tokm.baseform
        #print("### pos1-{}-idx-{}-".format(tokm.pos1, dic_idx))  ####
        d.chunks[i].dictents = d.odict[tokm.pos1][dic_idx]
        #import pdb; pdb.set_trace()  ####

# デバッグ用ダンプ

def dump_blds():
    print("====== start build dump ======")
    print("---- chunks ----")
    for i,ch in enumerate(d.chunks):
      print("i:{} DA:{} HA:{} CM:{} ma:{} fu:{}".format(i, ch.has_aux_da,
         ch.has_topic_HA, ch.has_comma_last, ch.maintyp, ch.functyp))
    print("---- chunk_relation_tbl ----")
    n = len(d.chunks)
    for i in range(n-1):
      for j in range(n):
        print("i:{} j:{} lbl:{}".format(i, j, d.chunk_relation_tbl[i][j]))
    print("---- dep_eval_tbl ----")
    for i in range(n-1):
      for j in range(n):
        print("i:{} j:{} eval:{}".format(i, j, d.dep_eval_tbl[i][j]))

# 以上の 1)-4)をまとめて実行

def builddep():
    expand()
    extract_features()
    set_chunk_relations()
    set_dep_eval_tab()
    get_dictent()
    if DBG_BLD:
      dump_blds()
