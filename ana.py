# $Id: ana.py,v 1.51 2017-02-22 02:13:14 eikii Exp $
import data as d
import defdict as dd
from defdict import DepLbl
import blddep  # for maintok()
import srch  # for find_dictent_by_id()
import enum
from datetime import datetime as dt

#### FIXME ownobj 不使用なら obj に not_in_use つける
#          推論結果が既ノードと一致したらダブりをとる
#          Nomiのinvolved_inをセット

DBG_ANA = True
def dpr(msg):
  d.dbgprint(DBG_ANA, msg)

#### #### obj作成  regist_obj<コア> <-- create_ownobj<ownobj用>

def regist_obj(clsid):
    """ クラス clsid のObjエントリをobj_stackに作る """
    n = d.Nomi()
    #n.refexprs.append(clsid)
    n.refexprs = [clsid]
    n.attrs = {}
    d.obj_stack.append(n)
    return n


def create_ownobj(ch):
    """ 文節chに対応するownobjを作成（使わないかもだが） chがNOUNなことは既知とする """
    clsid = ch.dictents[ch.wsd]["id"]  # wsdwork[i]からch.wsdをセットしておく
    ch.ownobj = regist_obj(clsid)
    dpr("---- CreOwn cls:{}".format(clsid))


#### 属性obj作成  regist_attr<属性登録I/F> --> find_attr_obj<属性obj探し/作成>
#                                          +--> create_attr_obj<属性obj作成コア>

def create_attr_obj(owner_ob, attrid):
    """ オブジェクトownerの属性attridのobjを作成する（その属性は現在ないのが前提） """
    global toremove
    a = d.Attr()
    a.dict_id = attrid
    a.owner = owner_ob
    a.involved_in = []
    owner_ob.attrs[attrid] = a  # 注：attrs[]はハッシュ(attridが整数でも)
    d.obj_stack.append(a)
    toremove.extend([ ('dh', owner_ob.attrs, attrid), ('p', d.obj_stack) ])
    # aはPythonがGCする(?)
    dpr("---- CreAtrOb ob:{} atr:{}".format(owner_ob.refexprs[0], attrid))
    return a


def find_attr_obj(owner_ob, attrid):
    """ オブジェクトownerの属性attridのobjがあればそれを、なければ作成して返す """
    if attrid in owner_ob.attrs.keys():
        return owner_ob.attrs[attrid]
    else:
        return create_attr_obj(owner_ob, attrid)


def regist_attr(owner_ob, attrid, value):
    """ ownerオブジェクトに属性attridを定義する。値はvalue。定義した述語objを返す """
    global toremove
    attrobj = find_attr_obj(owner_ob, attrid) # 属性objがなければfind_..()が作る
    p = d.Pred()
    p.dict_id = attrid
    p.cases.append((d.DeepCase.AGENT, owner_ob))
    p.attr_value = value
    d.pred_stack.append(p)
    attrobj.involved_in.append(p)
    #toremove.expand([('d',p),('p', pred_stack),  # pはPythonがGCする(?)
    toremove.extend([         ('p', d.pred_stack), # 後で削除するものの情報を残す
                      ('p', attrobj.involved_in) ]) # 'd' -> del, 'p' -> pop
    dpr("---- RegAtr ob:{} atr:{} v:{}".format( \
                     owner_ob.refexprs[0], attrid, value))
    return p


#### objの属性読み出し  get_attrs<インスタンスの属性リストを返す>
#                       A-- get_attr<I/F まずobjを、なければクラスを見る>
#               get_default_attr<クラスのデフォ属性> <--+

def get_attrs(owner_ob, attrid):
    """ オブジェクトownerの属性attridの値定義Predのリストを返す """
    if attrid not in owner_ob.attrs.keys():
        return []
    aob = owner_ob.attrs[attrid]  # 属性obj
    # FIXME TBC クラスのデフォ属性も見る！
    return aob.involved_in


def get_default_attr(clsid, attrid):
    """ クラスclsidのobjの持つデフォルト属性attridの値を（あれば）返す """
    dictent = srch.find_dictent_by_id("名詞", clsid)
    # まず clsid のデフォ属性をみる
    if "デフォ属性" in dictent.keys():
        if attrid in dictent["デフォ属性"].keys():
            return dictent["デフォ属性"][attrid]
    # clsid にはなかったので、親階層のデフォ属性をみる
    if "親階層" not in dictent.keys():
        return None
    for parentid in dictent["親階層"]:
        atr = get_default_attr(parentid, attrid)
        if atr is not None:
            return atr
    # 親にもなかった
    return None

def get_attr(owner_ob, attrid):
     """ オブジェクトownerの属性attridの値を返す """
     # FIXME TBC 本来はTimeSpecが引数にあり、その時点の値を返すべき！今抜けてる
     ls = get_attrs(owner_ob, attrid)  # 値定義Predのリスト
     for p in ls:     # FIXME 今は単に最初のを返してる
         return p.attr_value  # 述語はDEFATTR、格はAGENTのはずなのでチェックしてない

     # FIXME TBC クラスのデフォ属性も見る！　下はかなりいい加減なtemp patch
     for clsid in owner_ob.refexprs:  # オブジェクトownerの定義クラスのリスト
        atr = get_default_attr(clsid, attrid)
        if atr is not None:
            return atr

     return None


#### 探索中に一時的に作成したobj/predを消す

def unregist_tmps():
    global toremove
    while toremove:   # リストが空になるまで
        ope = toremove.pop()  # 最後の要素を取り出す
        if ope[0] == 'd':   # ('d', a_hash["foo"]) -> 要素["foo"]を消す
            del ope[1]
        elif ope[0] == 'dh': # ('dh', a_hash, key) -> 要素a_hash[key]を消す
            del ope[1][ope[2]]
        elif ope[0] == 'p': # ('p', a_list) -> 最後の要素を消す
            ope[1].pop()


#### 照応候補作成に使う小道具

def dict_attr_id(str):
    return str   # 単語はシノニムがあるのでid必要だが、属性名はユニークにすればよい
    #return d.odict["属性"][str]

def is_male(ob):
    b = (get_attr(ob, dict_attr_id("gender")) == "男")
    return b
    #return (get_attr(ob, dict_attr_id("gender")) == "男")

def is_female(ob):
    return (get_attr(ob, dict_attr_id("gender")) == "女")

def ob_surface_match(ob, ch):
    """ オブジェクトobの表層と文節chの表層が一致するか（固有名詞の比較用） """
    ch_surf = blddep.maintok(ch).surface   # 文節の表層  FIXME maintok??
    for clsid in ob.refexprs:  # obの定義クラスのリストをなめる
        ob_surf = d.odict["index"][clsid]  # ob(のクラスの一つ)の表層
        if ob_surf == ch_surf:
            return True
    return False


#### 照応候補作成

def select_ana_cands(noownobj):
    global ana_cands
    ana_cands = [ [] for k in range(len(d.chunks)) ]

    for (i,ch) in enumerate(d.chunks):
        if ch.maintyp not in [d.MainType.NOUN, d.MainType.NOUNDAPRED]:
            continue  # 名詞だけ以下をやる

        #左から処理するので、ここで作れば、これより右を処理する時は必ず左文節がownobjを持つ
        cands = []
        found = False
        for ob in d.obj_stack:
            # obがchの照応候補か？   FIXME 全objでなく、最近の＋NERだけ、とか？
            if isinstance(ob, d.Attr):  # FIXME temp とりあえずAttrは無視
                continue
            iscand = False
            if ch.pronoun_animate:  # FIXME 代名詞全般にせよ！今は人のみ
                #if ch.ownobj is ob:
                #    dmy = 0         # この文はダミー：代名詞ならownobjはなし
                #elif ch.pronoun_male:
                if ch.pronoun_male:
                    if is_male(ob):   # FIXME? femaleでなければ、か？
                        iscand = True
                elif ch.pronoun_female:
                    if is_female(ob):   # FIXME? maleでなければ、か？
                        iscand = True
                # FIXME TBC else...   疑問詞ならcand出さない、がいるのでは？
            elif ch.named_entity:
                if ob_surface_match(ob, ch):
                    iscand = True
            # FIXME TBC else:  一般名詞

            if iscand:
                found = True
                cands.append(ob)

        # obj_stackは終わり。次、ownobjどうするか   *noownobjならownobj作らない(QA用)
        if not noownobj and \
          (ch.named_entity and not found or \
           not ch.named_entity and not ch.pronoun_animate ):
            create_ownobj(ch) # ownobj作成 FIXME 名詞だけ？述語文節はどうする？
            cands.append(ch.ownobj)

        ana_cands[i] = cands

    if DBG_ANA:
        dpr("[][] after select_ana_cands:")
        anacands_dump()

#### obj/pred stackのダンプ

def dump():
    stack_dump()
    anacands_dump()

def stack_dump():
    print("**** obj_stack>")
    for ob in d.obj_stack:
        if isinstance(ob, d.Nomi):
            print("Ob ref{}{} atrs:{} inv:{}".format(ob.refexprs[0], ob, \
              ob.attrs if "attrs" in dir(ob) else None, \
              ob.involved_in if "involved_in" in dir(ob) else None))
        else:  # Attr
            print("At id:{} ow:{}".format(ob.dict_id, ob.owner.refexprs[0]))

    print("**** pred_stack>")
    for p in d.pred_stack:
        print("dic{}{} cases:{} val:{}".format( \
      p.dict_id, p, p.cases, p.attr_value if "attr_value" in dir(p) else '--'))

def anacands_dump():
    print("**** ana_cands>")
    str = ""
    for (i, obls) in enumerate(ana_cands):
        str += "ch[{}]: ".format(i)
        for ob in obls:
            str += "-{}, ".format(ob.refexprs[0])  # 最初の定義のクラスID
        str += "\n"
    print(str)


#### 述語エントリ作成
#  regist_ordinary_pred<pred作成コア> <-- regist_attr_pred<属性述語用,述語すげ替え>
#    A-- create_pred<文節に対するpred作成;属性述語か否かで切分け> --A
#            A-- create_preds<文中の全ての文節の述語を作成>

class ScalarValue:
    def __init__(s, str):
        s.str = str
    # FIXME TBC 比較メソッド等


def regist_ordinary_pred(ch):
    """ 動作動詞の文節chに対応する述語スタックのエントリを作成 """
    global toremove
    p = d.Pred()
    p.sent_cnt = d.sent_cnt
    p.chsuf = ch.chsuf
    p.dict_id = ch.dictents[ch.wsd]["id"]  # FIXME? メソッドにする?
    p.created_at = dt.now()
    if ch.tense_past:
        p.timespec = d.TimeSpec()  # FIXME 「created_atより前」
    #else  FIXME TBC 非過去のときのTime
    # 格補語
    for paaent in ch.paasrces:   # paaent: (srcch, case)
        caseobj = d.chunks[paaent[0]].ana
        p.cases.append((caseobj, paaent[1]))   # (anaobj, case)
        # FIXME TBC 連用修飾、副詞節  caseobj.involved_inにも追加
    d.pred_stack.append(p)
    toremove.append(('p', d.pred_stack))
    return p


def regist_attr_pred(ch, predid):
    p = regist_ordinary_pred(ch)
    p.dict_id = predid   # 怒る -> 怒っている、等


def create_pred(ch):
    """ 文節ch（述語）に対して,述語スタックのエントリを作成 """
    meandic = ch.dictents[ch.wsd]
    #meandic: {"id": XX, "名詞親和度": XX, "属性変化": T/F,
           #    "対応属性": attrid, ...  *対応属性は属性変化=Tの時のみ
           # or "属性述語": predid, ... }
    attr_chg_pred = meandic["属性変化"]
    if attr_chg_pred and ch.aspect_TEIRU:  # 属性変化動詞＋テイル -> 属性定義
        # 「怒っている」 -> AGENT objに「怒っている」属性をつける
        if "対応属性" in meandic.keys():
            # FIXME? このブロック、今使ってない 2017-02-17
            attrid = meandic["対応属性"]
            agent_ob_list = [ d.chunks[paaent[0]].ana for paaent in \
                              ch.paasrces if paaent[1] == srch.DeepCase.AGENT ]
            deg = ScalarValue("普通")  # 程度指定  FIXME temp ちゃんと書け！
            regist_attr(agent_ob_list[0], attrid, deg)
        else:
            newpredid = meandic["属性述語"]
            regist_attr_pred(ch, newpredid)
    # FIXME more 形容詞->属性、NOUNDAPRED等
    else:
        regist_ordinary_pred(ch)


def create_preds():
    """ 文節を*右*からなめ、述語ならcreate_pred()を呼ぶ """
    # ..ん？左からか？で、左からの推論結果で右のをチェック？
    #  - まず右から、(obj属性なしで、文法的に)factuality関連情報だけ伝播させ、
    # 　その後で左から解釈、か？
    n = len(d.chunks)
    sum = 0
    for i in range(n-1, -1, -1):   # n-1, n-2, ... , 1, 0
        ch = d.chunks[i]
        if dd.chunk_is_pred(ch):
            create_pred(ch)
            sum += consistency_point()  # スタックtopの[今入れた]predが対象
    return sum


#### マッチ＋評価用の小道具

def pred_case_ob(p, cas):
    """ 述語pの、格casのobjを返す """
    for ob_cas in p.cases:
        if ob_cas[1] == cas: #FIXME? 最初に見つけたのだけで良いか?(重複ないならok?
            return ob_cas[0]
    return None

CTX_MCH_POINT = 15
CAUSE_MCH_POINT = 30

#### マッチ＋評価

def consistency_point():
    """ pred_stackのトップの述語が、それまでの述語とどの程度整合的かの得点を返す """
    # pred_stackのトップが対象
    sz = len(d.pred_stack)
    curp = d.pred_stack[sz-1]  # 今見ている（トップの）述語
    ch = d.chunks[curp.chsuf]  # 「〜からだ」情報のため FIXME それもpredに持つか？
    sum = 0
    for k in range(sz-2, -1, -1): #対象より前のpred全てとマッチを見る(直近の方から)
        oldp = d.pred_stack[k]   # 比較する、以前の述語
        if curp.dict_id != oldp.dict_id:    # 述語がマッチ?
            continue
        # 述語がマッチした。格補語見る
        mch = True
        for cur_ob_cas in curp.cases:
            cand_ob = pred_case_ob(oldp, cur_ob_cas[1])
            if cand_ob is not None and cand_ob != cur_ob_cas[0]:
                mch = False   # objが別ならマッチでない。格がないのはok
                break
        if not mch:
            continue
        # 述語、格補語ともマッチした  FIXME テンス(TimeSpec)、否定、モダリティも
        sum += CTX_MCH_POINT

        #　「～からだ」文なら、curpが直前の文の理由かをみる FIXME 直前？複文なら?
        if ch.has_aux_da and ch.has_ppconj_KARA:  #「～からだ」文 FIXME ループ外へ?
            p2 = oldp  # oldpから推論元をさかのぼって辿る　原因/前提のみ
            is_cause = True
            while "inf_parent_type" in dir(p2):
                if p2.inf_parent_type not in ["原因", "前提"]:
                    is_cause = False
                    break
                p2 = p2.inf_parent_pred
                if "sent_cnt" in dir(p2):  # 推論結果でなく、入力文の述語
                    is_cause = (p2.sent_cnt == d.sent_cnt - 1) # 直前の文の原因か
                    break
            if is_cause:
                sum += CAUSE_MCH_POINT
    return sum


#### 推論展開

CAS2DEEPCAS = { "主格": d.DeepCase.AGENT, "対格": d.DeepCase.OBJ,
                "与格": d.DeepCase.GOAL  }

def apply_inference():
    global toremove
    # FIXME これだとまだ１段だけ。深さdepまで、とかにする
    for p in d.pred_stack[d.pred_stack_size_orig:]:  # anaeval後にできたpredのみ
        #pred_dict = d.odict["動詞"][p.dict_id]  # 述語の辞書エントリ
        pred_dict = srch.find_dictent_by_id("動詞", p.dict_id) #述語辞書エントリ
        # inf {type:前提, pred:<推論先述語の述語id>, 主格: 推論元述語での主格,..}
        for inf in pred_dict["推論"]:   # 述語に付随の推論ルールをなめる
            pp = d.Pred()  # 推論先の述語エントリ
            pp.dict_id = inf["pred"]
            for cas in inf.keys():
                if cas not in ["主格", "対格", "与格"]:
                    continue
                # 推論元の格&obj  * p.cases: [ (caseobj, case) ]
                srccaseobj_ls = [x[0] for x in p.cases if
                                                x[1] == CAS2DEEPCAS[inf[cas]]]
                dstcase = CAS2DEEPCAS[cas]        # 推論先での格
                if srccaseobj_ls:
                    pp.cases.append((srccaseobj_ls[0], dstcase))
            pp.inf_parent_type = inf["type"]  # 推論の種類
            pp.inf_parent_pred = p            # 推論元の述語
            d.pred_stack.append(pp)
            p.infer_results.append(pp)  # 推論元に「この述語を推論した」と記録
            # FIXME TBC more TimeSpec,...
            toremove.extend([('p', d.pred_stack), ('p', p.infer_results)])

####

def anaeval(val):
  valdiff = create_preds()
  return val + valdiff

####

def ana_qa():
    """ 現在の文をクエリとして解釈し、回答する """
    # dep/pawsはセットされてる前提

    dpr('&&&& &&&& QA &&&& &&&&')
    n = len(d.chunks)

    select_ana_cands(True)   # ana候補生成　　arg: ownobj作らない

    # 照応にあいまい性があったら当面パス
    if max([len(x) for x in ana_cands]) >= 2:
        print("ambiguous question")
        return

    # chのobjをセット
    for i in range(n):
        if d.chunks[i].maintyp == d.MainType.NOUN and \
           not d.chunks[i].pronoun_interrogative :  # 格補語の検出 FIXME bogus!
            d.chunks[i].ana = ana_cands[i][0]

    # 質問がWHかYNかをみる   FIXME どっちでもなかったら？（当面無視）
    is_wh_ques = False
    for i in range(n):
        if d.chunks[i].pronoun_interrogative:
            is_wh_ques = True
    is_yn_ques = not is_wh_ques and d.chunks[n-1].has_ppterm_KA

    # 過去の述語をなめる
    cands = []
    ch = d.chunks[n-1]    # FIXME 当面、述語は最後の文節と決め打ち
    ch_dic_id = ch.dictents[ch.wsd]["属性述語" if ch.aspect_TEIRU else "id"]
    for p in d.pred_stack:
        # 質問文の各文節をみる。FIXME 当面述語と格補語のみを仮定
        mch = True
        cand = None
        if ch_dic_id != p.dict_id: # 述語がマッチしなければこの過去文は無関係、次の文へ
            continue
        for paaent in ch.paasrces:   # paaent: (srcch, case)
            srcch = paaent[0]
            cas   = paaent[1]
            pred_ob = pred_case_ob(p, cas)
            if d.chunks[srcch].pronoun_interrogative:
                cand = pred_ob
            elif d.chunks[srcch].ana is not pred_ob:
                mch = False
                break

        if mch and is_yn_ques:
            print('はい')
            return

        if mch and cand is not None:
            cands.append(cand)

    if is_yn_ques:
        print('いいえ')
        return
    # is_wh_ques
    if cands:
        stri = ""
        first = ""
        cands_set = set(cands)    # 重複除去　FIXME やるのここか？
        for c in cands_set:
            stri += first + str(c)
            first = ", "
        print(stri)
    else:
        print('該当がありません')

    dpr('&&&& &&&& QA END &&&& &&&&')
