# $Id: defdict.py,v 1.6 2017-02-01 06:12:27 eiki Exp $

import enum
import data as d

#### とりあえず必要なクラスを書き出してく。後で適切なファイルに移す
# ターゲット：
# ダニエルはボールを拾った　　ジムはケビンに怒鳴った　彼は怒っていたからだ

#### （広義の）モダリティ；　テンス、アスペクト、否定、ボイス、モード

class Modality:
  def __init__(s):
      x = 0  # FIXME dummy

#### 係り受け種類ラベル

DepLbl = enum.Enum("DepLbl", [

"INVALID",  # ありえない

"RENTAI_NO", # 連体修飾（名詞＋ノ）
"RENTAI_ADJ", # 連体修飾（動詞・形容詞の連体形、連体詞）
"RENTAI_CLAUSE", # 連体修飾（連体節）

"RENYOU_ADV", # 連用修飾（形容詞の連用形、副詞）
"RENYOU_CLAUSE", # 連用修飾（副詞節）

"CASECOMP", #  格補語

"NOUN_CONCAT", #  複合名詞
"NOUN_EQUIV", #  名詞の同格
"NOUN_PARA", #  名詞の並列
"PRED_PARA",  #  述語の並列

"FWD_CONJ",   # 順接
"REV_CONJ",   # 逆接

"NONE" # 係り受けなし
])

 #### 述語項タイプのラベル

PAA_INVALID = 0 # ありえない

  # 主格        対象格         経験者格        時間格         場所格
PAA_AGENT = 1; PAA_OBJ = 2;  PAA_EXP = 3;  PAA_TIME = 4;  PAA_LOC = 5

  # 源泉格      目標格          道具格          使役者格
PAA_SRC = 6;  PAA_GOAL = 7;  PAA_INST = 8;  PAA_CAUSER = 9;

PAA_NONE = 10  # 格なし

 #### 文節クラス

class Chunk:
  def __init__(s):
      s.depsrces = []  # 係り元リスト
      s.depdst = None  # 係り先
      s.deplbl = None  # 係り受けタイプ
      s.dict_surface = None  # 表層辞書エントリ
      s.wsd = 0      # 意味（表層の意味リスト中の何番めか）
      s.anaphora = None  # 照応先オブジェクト
      s.paasrces = []  # 格補語リスト（述語に対して）　エントリ：（文節番号(or -1),obj）
      s.paadst = None  # 格補語に対して、それが係る述語

def chunk_is_pred(ch):
  return (ch.maintyp in [d.MainType.VERB, d.MainType.ADJ,d.MainType.NOUNDAPRED])

#### 辞書：表層    注：単語文字列自体と品詞は本来不要（前者はインデックス、後者は別配列なので）

class DictSurface:
    def __init__(s):
        s.str = ""    # 単語文字列自体（デバッグ表示用）
        s.meaning = []  # 対応する意味エントリのリスト　WSDはこれのインデックスを返す

#### 辞書：名詞意味    注：表層、品詞は不要（のはず）

class DictNoun:
    def __init__(s):
        s.parents = []    # この名詞の親階層である名詞クラスのリスト
        s.defo_attrs = []    # この名詞が標準で持つ（属性、値）のリスト

#### 辞書：動詞意味    注：表層、品詞は不要（のはず）

class DictVerb:
    def __init__(s):
        s.parents = []    # この動詞（/形容詞）の親階層である動詞クラスのリスト
        s.attr_chgs = []  # 属性変化の記述　要素はAttrChg

#### 辞書：属性意味

class DictAttr:
    def __init__(s):
        s.parents = []    # この属性の親階層である属性クラスのリスト

#### 属性変化（動詞辞書の中）

ATTRDIR_INVALID, ATTRDIR_HI, ATTRDIR_LO, ATTRDIR_UP, ATTRDIR_DN = range(5)

class AttrChg:
    def __init__(s):
        s.changer = None    # 属性が変化する格
        s.direction = 0    # 属性変化の高低/方向　ATTRDIR_***
        s.arg = None    # 属性の引数にバインドされる格
