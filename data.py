# $Id: data.py,v 1.35 2017-02-21 04:53:04 eikii Exp $
import enum

# デバッグ用print関数
def dbgprint(flag, msg):
    if not flag:
        return
    print(msg)
## 

MainType = enum.Enum("MainType", [
  "NOUN",    # 名詞
  "NOUNDAPRED",    # 名詞 + 判定詞
  "VERB",    # 動詞
  "ADJ",     # 形容詞
  "ADNOM",    # 連体詞
  "ADV",     # 副詞
  "CONJ",     # 接続詞
  "INTERJ"     # 感動詞
])

DeepCase = enum.IntEnum("DeepCase", [
  "AGENT",  "OBJ", "GOAL", "SRC", "TIME", "LOC", "INSTR", "CAUSER", # EXPERI?
  "NONE" ])

# データ構造の定義

#### #### 名詞オブジェクト/述語テーブル

# 名詞オブジェクト、述語、複合述語のいずれか
class Item:    #
    def __init__(s):
        s.id = 0  # int  FIXME! idを割り振る

# 名詞オブジェクト
#   "NomiComp"はない(文節構造にはある)；「AとBがXした」->「AがXした & BがXした」、等
#   FIXME 実在/仮定 いるか？（不要？）
class Nomi(Item):    # nominal
    def __init__(s):
        s.attr_effects = []    # [Pred] 属性（関係）の定義/変化を示す述語のリスト
            # これをなめて属性スナップショットを作る  FIXME case_refsからのジェネレータ?
            # 集合/統合/離脱/分離、所属/部分 も属性としてsnapに入れる
            # IDENT(同一)関係もやはりsnapに　※「変身」ケース（雪兎と月とか）は別objのまま
            # 「何か」「誰か」も、カテゴリに UNK を定義し、やはりsnapで表す
        s.flags = []       # [bool(?)] 全称、（あとは？）　　不定はattr_effで。
        s.pred  = None     # Pred (or None) 述語に対応する時、その述語
                           #     連体節・名詞節、以前の述語の照応
        s.cache_time = None   # TimeSpec スナップショットが対応する時刻
        s.cache_snap = None   # [(Attr, AttrValue)] スナップショット
                              # FIXME 所属カテゴリもいる！
          # ※各カテゴリのスーパークラスは辞書コンパイル時(?)にあらかじめリストアップしておく
        #以下は文節構造の方に持つ
        #s.case_refs = []   # [CaseRef] 自身が格補語として登場した述語(/連体ノ)のリスト
        #s.modifiers = []   # [CaseRef?] これに係る形容詞/連体節/連体ノのリスト

    def __lt__(s,y):   # FIXME?  cmp needed to avoid err
        return (s.refexprs < y.refexprs)

    def __repr__(s):
        global odict
        clsid = s.refexprs[0]
        return odict["index"][clsid]

# 述語単体
class Pred(Item):    # predicate
    def __init__(s):
          # 基本情報
        s.dict_id = None  # int? DictHand[Verb/Adj/Attr]?  辞書中の述語ID
                # 定義済み述語も含む： V_HI/LO/UP/DN/UNK  何かをする DO_UNK も
                #    DEF_ATTR_VAL  属性への値定義
                #    COPULA_CATEG/IDENT　名詞述語：　属するクラスか、objとしての同一性
        s.created_time = None   # 絶対（システム）時刻　このPredが作成された時刻
        s.source = None   # (Pred<Comp>/Sent, InferRule)
                          #    元になった文/推論元述語(w/ルール)
        s.receivers = []   # [Nomi] 情報の受け手リスト（デフォは話の聞き手）
        s.infer_results = []  # [(InferRule, [Pred])]ここからの推論結果のリスト
                              #   ※この要素を、推論元と先から共有するか？
        s.clause_type = None  # ClauseType 不定詞や連体節/名詞節の述語であることを示す
        s.nomi = None     # 連体節や名詞節等で、対応するNomiがあるならそれを指す
        s.replaced_by = None  # 格補語だけ修正したような時、その修正した新たな述語を指す
        #s.factuality = None    # FIXME??? 関数にする? claustypとテンスから。
          # 文末表現要素
        s.negation = False    # bool 否定
        s.modality_is_ques_yn = None    # bool Y/N疑問かどうか
        #s.modality_wh_ques_elems = []   # [FIXME パスリスト?] WH疑問要素のリスト
        #   - 関数でよいか？
        s.modality_confidence = None    # ModalConfidence  推量モダリティ
                                        #  FIXME 時間で変わる？ならリスト？
        s.aspect_progr = None    # (..essive) bool  進行中アスペクト（対動作）
            # ※経験 - 単なる過去　＋　「知ってる」ことを推論(?)
        s.time_specs = [] #[TimeSpec] 時間指定のリスト ※含テンス アスペクトは推論結果?
          # 各種関係（格補語、文間、修飾、etc）
        s.attr_val = None  # AttrValue 述語が属性値定義の時、その値
        s.attrs = [] #[(Attr, AttrValue)] 述語の属性(様態)リスト 疑問:なぜ,どのように
        s.cases = []    # [(CaseType, Item)] 格補語のリスト focus(主題)もマーク
            # 複合動詞/意志/働きかけ：「食べ(ることをし)たい」と考え、不定詞を目的語に
            # 属性の引数（「親しい(Xと)、みたいの）も格補語のように扱う
        s.relations = []  # [Relation] 文間関係のリスト　複文も文間もここで扱う
                          #  質問->回答 もここで扱う
        #s.modifies = None    # 連体節(/名詞節?)の係り先　ー文節構造の方？
        #s.speaker = None  # Nomi 話者オブジェクト　ー文節構造の方へ

    def __str__(s):  # Note: any difference between __repr__ and __str__?
        global odict
        clsid = s.dict_id
        return odict["index"][clsid]


# 複合述語　複数の述語をif,and,or,not,seqで組み合わせ
# 　　　　　主にシナリオ推論から出てくる(if以外は) ※ifはどこから？
class PredComp(Item):    # predicate composite
    def __init__(s):
        s.comp_typ = None    # TBC if/and/or/not/seq/...
        s.elems = []       # TBC 結合される述語のリスト


# 属性  - dict.py へ移すか？
class Attr:    # attribute
    def __init__(s):
        s.dict_id = 0    # TBC 属性の辞書中のエントリを指すid
        s.owner = 0    # TBC 属性の持ち主オブジェクト

# 属性値
class AttrValue:    # 属性の（スカラ）値　　　FIXME? 範囲、も？　　疑問は？　単位要る?
    def __init__(s):
        s.is_abs = 0         # フラグ 絶対or相対 FIXME最上級も!　他に持つべきフラグは?
        s.direction  = None    # 相対の場合の方向　〜より小/大/ジャスト
        s.precision  = None    # 精度　大体〜、ちょうど、…
        s.base  = None         # 相対の場合の基準
        s.value = None         #  floatの他、少し/かなりとかも

# 節の分類
class ClauseType:    #
    CLTYP_INVALID = 0
    CLTYP_PLAIN   = 1   # 単文、重文、複文の主節、理由節 - 単独で事実性を見る
    CLTYP_NOMINAL_NO = 2  # 名詞節 ノ、コト - 対応するNomiに事実性の属性をつける
    CLTYP_NOMINAL_KA = 3  # 名詞節 カ - 事実性なし（というか N/A というか）
    CLTYP_NOMINAL_QUOTE = 4  # 名詞節 ト - 対応するNomiに事実性の属性をつける
    CLTYP_ADNOMINAL = 5 # 連体節 - (限定なら)仮定的;修飾するNomiに対しては真としてよい
    CLTYP_TIME = 6      # 時の副詞節 - 主節が事実なら事実
    CLTYP_COND = 7      # 条件の副詞節 - ト/タラ〜した、なら事実。それ以外なら未実現
    CLTYP_INFIN = 8     # 不定詞 - 事実性なし（N/A）
    def __init__(s):
        s.dict_id = 0    # FIXME dummy TBC

# 文間関係
#class Relation:    #

# 推論規則
#class InferRule:    # inference rule

# 推量モダリティ
class ModalConfidence:    # modality confidence
    def __init__(s):
        s.info_reliability = 0  # float この情報の信頼度  ※AttrValue? floatで十分?
        s.src_reliability = 0   # float 情報源オブジェクトの信頼度
        s.source = None         # Nomi 情報源オブジェクト  FIXME?「聞いた」等の述語?

# 時間  - timespec.py へ移すか？
class TimeSpec:    # time specifier　FIXME 反復、習慣、普遍的真理も
    def __init__(s):
        s.is_abs = 0           #  フラグ 絶対or相対  　他に持つべきフラグあるか？
        s.question = 0         #  　疑問「いつ」
        s.direction  = None    #  相対の場合の方向　〜より前/後ろ/ジャスト
        s.precision  = None    #  精度　大体〜、ちょうど、…
        s.base  = None         #  相対の場合の基準
        s.time_value  = None   #  相対の場合の基準との時刻差、絶対の場合の時刻

# 名詞オブジェクトへの格補語参照
#class CaseRef:    #
#    def __init__(s):
#        s.id = 0           # int 本エントリ自体のid
#        s.case_type = 0    # enum どの格かを表す CS_SUBJ 等
#        s.modified = None  # Pred/Nomi この述語(/連体ノ)の係り先
#        s.nomi = None      # Nomi 係り元（格補語）である名詞オブジェクト
                           #      誰、何、どこ、いつ等の疑問も表す

#### #### cabocha インタフェース  - cabocha.py へ移すか？

class Token:
    def __init__(s):
        # 0:3 品詞分類1-4  4 活用種  5 活用形 6 基本形  7 読みがな  8 発音
        # pos1-4 cjtype cjform baseform kana pronou
        s.surface = ""
        #s.normalized_surface = ""  cabocha入力にない!

class CabChunk:
    def __init__(s):
        s.token_size = 0  # この文節に含まれる形態素の個数
        s.token_pos = 0   # この文節の先頭の形態素の位置
        s.head_pos = 0    # 主辞の位置（この文節の先頭から数えて）
        s.func_pos = 0    # 機能辞の位置（この文節の先頭から数えて）
