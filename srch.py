# $Id: srch.py,v 1.67 2017-02-21 06:37:10 eikii Exp $
import heapq, copy, enum
import data as d
import defdict as dd   # FIXME remove defdict!
from defdict import DepLbl   # FIXME? now needed for DepLbl
#from ana import anaeval, select_ana_cands
import ana
from data import DeepCase

DBG_DEPSRCH = True
def dpr(msg):
  d.dbgprint(DBG_DEPSRCH, msg)

HEAPSIZE = 30  # FIXME temp
TOPIC_HA_FOR_ADNOM_CLAUSE_COST = 25  # FIXME bogus, tune

def depsrch(m, acc):    # 文節 m からの係りを変えてサーチ
    global chunks_length, depwork, dep_heap
    dpr(";; DEPSRCH m:{} ac:{}".format(m,acc))
    n = chunks_length
    if m == -1:  # リーフ。評価する
        # 係り一つでわかる点数はaccに入っている。係り２つ以上によるもののみ計算。
        # 現在の係り方は depwork[] に入っている
        for i in range(n-2):
            j = depwork[i]
            dpr(";; DEPSRCH-leaf i:{} j:{}".format(i,j))
            if j<n-1 and d.chunks[i].has_topic_HA and \
               d.chunk_relation_tbl[j][depwork[j]] == DepLbl.RENTAI_CLAUSE :
                acc -= TOPIC_HA_FOR_ADNOM_CLAUSE_COST   # ハ格は連体節にはない
        # FIXME TBC more...
        # accに評価値が入った。ヒープへ格納
        if len(dep_heap) < HEAPSIZE:
            heapq.heappush(dep_heap, (acc, copy.deepcopy(depwork)))
        else:
            heapq.heappushpop(dep_heap, (acc, copy.deepcopy(depwork)))
        return

    # m != 0 (m>0) ケース(非リーフ)
    #　係れない添字（クロス）を探す
    cross = [False] * n

    # i(<m)からの係り ... i->j(>m) に係るなら、mからj+1以上には係らない
    #                     (j<=mなら無視して良い）
    for i in range(m):
        if depwork[i] > m:
            for j in range(depwork[i]+1, n):
                cross[j] = True

    # i(>m)からの係り ... i->jに係るなら、mから[i+1, j-1] が係り不可
    for i in range(m+1, n-2):  # n-2はN/A
        for j in range(i+1, depwork[i]):
            cross[j] = True

    dpr(";; DEPSRCH xs:[{} {} {}]".format(cross[0], cross[1],
                                          cross[2] if len(cross)>=3 else '-'))

    # mからの係り先を動かしてサーチ
    for i in range(m+1, n):
        if cross[i] or d.chunk_relation_tbl[m][i] == DepLbl.INVALID :
            continue    # クロスか係り不可ならスキップ
        depwork[m] = i    # 係って、
        depsrch(m-1, acc + d.dep_eval_tbl[m][i])  # 子ノードをサーチして、
        depwork[m] = m    # 係りを戻す

####

def depsrch_root():
    global chunks_length, depwork, dep_heap
    chunks_length = len(d.chunks)
    n = chunks_length
    depwork = [ i for i in range(n-1) ]  # [0,1,...,n-2] 自分を指す <-> N/A
    dep_heap = []
    depsrch(n-2, 0)   # -> dep_heapにベストN解が入る

    if DBG_DEPSRCH:
        heapcpy = copy.deepcopy(dep_heap)
        sz = len(heapcpy)
        for i in range(sz):
            x = heapq.heappop(heapcpy)
            print("pt:{} [".format(x[0]))
            for j in x[1]:
                print("{} ".format(j))
            print("]\n")

#### 述語項解析

def select_deepcase(srcch, dstch):
    """ 格補語文節(src)と述語文節(dst)から、深層格を決定 """
    scas = srcch.ppcase  # 格助詞 "が"、"を"、等　または ""
    dvc = dstch.voice_causative
    dvp = dstch.voice_passive    # 述語の使役/受身
    cas = DeepCase.NONE
    if scas == "が":  # 彼が食べられた -> 彼はOBJ  食べさせた->CAUSER
        # 食べさせられた、食べた -> AGENT
        cas = DeepCase.OBJ    if dvp and not dvc else  \
            DeepCase.CAUSER if dvc and not dvp else  \
            DeepCase.AGENT    # dvp && dvc || !dvp && !dvc
    elif scas == "を":
        cas = DeepCase.OBJ
    elif scas == "に": # 彼に食べられた -> 彼はAGENT  彼に食べさせた->AGENT
        # 彼に食べさせられた -> CAUSER 彼に言った -> GOAL
        cas = DeepCase.GOAL    if not dvp and not dvc else  \
              DeepCase.OBJ     if dvp and dvc else DeepCase.AGENT
    elif scas == "から":
        cas = DeepCase.SRC
    # FIXME TBC より、…  迷惑受身どうする？
    return cas

# FIXME data.pyへ移す？
def find_dictent_by_id(pos, id):   # pos:"名詞"、とか　id:辞書中の単語のid
    ls = d.odict[pos][d.odict["index"][id]] #idの単語(の表層)が持つ意味のリスト
    for meanent in ls:
        if meanent["id"] == id:
            return meanent
    raise ValueError("no entry for id:{}".format(id))

def noun_match(nid, clsid):  # 名詞nidはクラスclsidに属するか
    if nid == clsid:
        return True
    nent = find_dictent_by_id("名詞", nid)
    for parent_id in nent["親階層"]:
        if noun_match(parent_id, clsid):
            return True
    return False

def ncv_point(nchsuf, cas, pchsuf): # 名詞　格(DeepCase)　述語 FIXME　代名詞/名詞節
    # pch.dictents[wsd] :
    #  { "名詞親和度": {"主格": {"人"id:4, "組織"id:3}, "目的格": ...},
    #    "id": 132 }                       A 降順ソートされてる
    global wsdwork
    #import pdb; pdb.set_trace()
    nch = d.chunks[nchsuf]
    pch = d.chunks[pchsuf]
    deepcase_str = ["", "主格", "対格", "与格"]  # FIXME more...

    # FIXME!!! temp patch
    COST_BAD_CASE = 888     # 格補語の格が辞書になかったらペナルティ
    if deepcase_str[cas] not in pch.dictents[wsdwork[pchsuf]]["名詞親和度"]:
      return (- COST_BAD_CASE)

    noun_affin = pch.dictents[wsdwork[pchsuf]]["名詞親和度"][deepcase_str[cas]]
    #{人id:4,..
    for nid_val in noun_affin.items():  # items()はタプル(key,value)のリストを返す
        #clsid = nid_val[0]  # 上の例だと：人id
        clsid = int(nid_val[0])  # FIXME tmp fix: somehow ..[0] is str, not int
        val = nid_val[1]    #           4
        if noun_match(nch.dictents[wsdwork[nchsuf]]["id"], clsid):
            return val
    # FIXME? 述語の親がより大きい可能性は？当面無視で良いか
    COST_INPROPER_NCV = 55  # FIXME tune
    return (- COST_INPROPER_NCV)


## PAAの格補語候補をリストアップ　＆　格補語->述語 の評価値を計算

BIAS4AGT = 2

def set_paa_tbls():
    global paa_eval_tbl, depwork, wsdwork, paawork, loop_stack
    dpr("@@ set_paa_tbls() started")
    n = len(d.chunks)
    for i in range(n):
        pch = d.chunks[i]    # 述語のみ対象
        if not dd.chunk_is_pred(pch):
               continue
        dicszi = len(pch.dictents)
        for j in range(i):   # j->iに（前から）係るのが対象
            if not (depwork[j] == i and
                    d.chunk_relation_tbl[j][i] == DepLbl.CASECOMP):
                continue   # 格補語以外スキップ
            nch = d.chunks[j]
            cas = select_deepcase(nch, pch)

            # 格候補が決まった。(格補語文節、候補格リスト)を登録する
            # 一つならpaaworkに直接書く。二つ以上ならとりあえずloop_stackに入れる
            if cas != DeepCase.NONE:  # 格補語あり、候補格一つのケース
                caselist = [cas]
                paawork[i].append((j, cas))
                dpr(">> paawk[{}] << ({}, {})".format(i, j, cas))
            else:   # デフォでAGENTとOBJ。述語の単語見ないで決める（必要なら後ではじく）
                caselist = [DeepCase.AGENT, DeepCase.OBJ, DeepCase.GOAL]
                loop_stack.append(
                    LoopStackEntry(SrchType.PAA, i, caselist, j) )
                dpr(">> LSE << (PAA, {}, [AGT,OBJ,GOL], {})".format(i, j))

            # この格関係による評価値をまとめて計算しておく。可能なwsd候補全てやっとく
            dicszj = len(nch.dictents)
            # paa_eval_tbl[i][j] = {} と初期化しておくこと
            for cs in caselist:
                paa_eval_tbl[i][j][cs] = [[0] * dicszj for k in range(dicszi)]
                # topicHAの時は主語を優先する FIXME 他で困らないか?(連体節等)
                paa_case_bias = BIAS4AGT \
                   if len(caselist)>1 and cs==DeepCase.AGENT else 0
                for iw in range(dicszi):
                  savi = wsdwork[i]   # wsdをセットしてから評価
                  wsdwork[i] = iw
                  for jw in range(dicszj):
                      savj = wsdwork[j]
                      wsdwork[j] = jw
                      paa_eval_tbl[i][j][cs][iw][jw] = ncv_point(j, cs, i) \
                                                       + paa_case_bias
                      wsdwork[j] = savj
                  wsdwork[i] = savi

            if DBG_DEPSRCH:
                 print("&&&& set_paa_tbls: i {} j {} szi {} szj {}".format(
                                           i, j, dicszi, dicszj))
                 for cs in paa_eval_tbl[i][j]:
                   for ii in range(dicszi):
                     for jj in range(dicszj):
                       print("i {} j {} cs {} ii {} jj {}: {}".format(
                         i, j, cs, ii, jj, paa_eval_tbl[i][j][cs][ii][jj]))

        #if DBG_DEPSRCH:
        #    #import pdb; pdb.set_trace()
        #    print("i {} wsdwk {} paawk ({}, {})".format(
        #           i, wsdwork[i], paawork[i][0], paawork[i][1]))

        # FIXME TBC i->j (iから係るj)でRENTAI_CLAUSEの時も！

    if DBG_DEPSRCH:
        print("!! loop_stack sz {}".format(len(loop_stack)))
        #for i in range(len(loop_stack)):
        #  print("i {} wsdwk {} paawk ({}, {})".format(

####

SrchType = enum.Enum("SrchType", ["WSD", "PAA"])
PAWS_HEAPSIZE = 200  # FIXME tune

class LoopStackEntry:
    def __init__(s, srchtyp, chsuf, candls, srcch):
        s.srchtype = srchtyp
        s.chunk_suf = chsuf
        s.cand_list = candls    # WSD: int   PAA: (srcch, case)
        s.srcch = srcch       # PAA only

def pawseval(val):
    # FIXME? ２文節間だけで評価できない要素はここで計算
    return val

def pawssrch(dep, val):
    global loop_stack, paws_heap, wsdwork, paawork, paa_dep
    if dep == -1:
        #storedata = (pawseval(val), copy.deepcopy(depwork),
        storedata = (pawseval(val), depwork,  # depwork(の先)は不変,コピー不要
               copy.deepcopy(wsdwork), copy.deepcopy(paawork))
        if len(paws_heap) < PAWS_HEAPSIZE:
            heapq.heappush(paws_heap, storedata)
        else:
            heapq.heappushpop(paws_heap, storedata)
        return
    elif dep == paa_dep - 1:
        # WSDからPAAに移る境界。固定のPAA要素の評価値をまとめて算入
        # (WSDの後でないと評価値が定まらない)
        assert ((dep == len(loop_stack)-1 or
                 loop_stack[dep+1].srchtype == SrchType.WSD) and
                loop_stack[dep].srchtype == SrchType.PAA     and
                -1 not in wsdwork                               )
        paasum = 0
        for i in range(len(d.chunks)):
            for paaent in paawork[i]:   # paaent: タプル(srcch, cas)
                paasum += paa_eval_tbl[i][paaent[0]][paaent[1]][
                             wsdwork[i]][wsdwork[paaent[0]]]
        val += paasum

    lse = loop_stack[dep]
    i = lse.chunk_suf
    ch = d.chunks[i]
    pwsd = wsdwork[i]
    COST_DUPLICATE_CASE = 77  # FIXME tune

    if lse.srchtype == SrchType.WSD:    # WSD ケース
        for wsd in lse.cand_list:
            wsdwork[i] = wsd
            pawssrch(dep-1, val)  # WSD自体の評価値も考慮?照応の距離,名詞の類似度..
            wsdwork[i] = -1

    elif lse.srchtype == SrchType.PAA:   # PAA ケース
        for cas in lse.cand_list:
            valdiff = 0
            if cas in [paaent[1] for paaent in paawork[i]]:  # appendする前にやる
                valdiff -= COST_DUPLICATE_CASE      # 格のダブりはここで減点
            paawork[i].append((lse.srcch,cas))   # paaent: (srcch, cas)
            nwsd = wsdwork[lse.srcch]   # wsd[ch]はセットされてる前提
            # 今セットした格の評価値を足し込む
            valdiff += paa_eval_tbl[i][lse.srcch][cas][pwsd][nwsd]
            pawssrch(dep-1, val+valdiff)
            paawork[i].pop()

    #else 例外?   FIXME?

## 係り受け(depwork)を一つセットした後、述語項/WSDサーチを行う

def pawssrch_root(depval):
    global loop_stack, wsdwork, paawork, paa_eval_tbl, paa_dep
    dpr("@@ pawssrch_root() started")
    loop_stack = []
    n = len(d.chunks)
    wsdwork = [ 0 ] * n
    #paawork = [ [] ] * n
    paawork = [ [] for k in range(n) ]
    #paa_eval_tbl = [ [{}] * n for k in range(n) ]
    paa_eval_tbl = [ [{} for m in range(n)] for k in range(n) ]

    # wsdを先に決めるようにするのだが、srchはdep=n側からやるので、
    # loop_stackにはPAAから先に積む

    set_paa_tbls()  # PAAの各種データをセット
    paa_dep = len(loop_stack)  # loop_stackでのPAAとWSDの境界を記憶しておく

    for i in range(n):   # WSD
        ch = d.chunks[i]
        sz = len(ch.dictents)
        if sz > 1:   # 複数意味あり、WSD必要
            wsdwork[i] = -1
            # FIXME 本来はそのwsd選択肢の評価値を入れるべき   第四引数はpaa用、ここはdmy
            loop_stack.append(LoopStackEntry(SrchType.WSD, i, range(sz), 0))
        else:
            wsdwork[i] = 0   # 意味は一つのみ、wsd=0

    pawssrch(len(loop_stack)-1, depval)   # 係り受けの評価値を渡す

## paws_heapを用意し、depworkを一つセットしてからpawssrch_rootを呼ぶ

def pawssrch_heap():
    global paws_heap, dep_heap, depwork
    dpr(">> pawssrch_heap() started  depheapsz:{}".format(len(dep_heap)))
    paws_heap = []
    for depans in dep_heap:  # FIXME 値の大きい順に呼ぶ方が良い
        depwork = depans[1]  # depans: (val, [dep array])
        pawssrch_root(depans[0])

    if DBG_DEPSRCH:
        paws_heap2 = copy.deepcopy(paws_heap)
        sz = len(paws_heap2)
        print("======== paws_heap result (size {}) ========".format(sz))
        for i in range(sz):
            x = heapq.heappop(paws_heap2)
            print("pt:{}".format(x[0]))
            print("dep: ", x[1])
            print("wsd: ", x[2])
            print("paa: ", x[3])

#### #### anasrch #### ####

ANA_HEAPSIZE = 5  # FIXME tune

def anasrch(dep, val):
    global paws_heap, ana_heap, depwork, wsdwork, paawork, anawork
    global analoop_stack
    if dep == -1:
        anawork_cpy = [ob for ob in anawork]
        ana.toremove = []
        # pred_stackのサイズを記録しておく(どこから新しい述語かの判定用)
        d.pred_stack_size_orig = len(d.pred_stack)
        ev = ana.anaeval(val)
        storedata = (ev, depwork,  wsdwork, paawork,
                     anawork_cpy)
               #copy.deepcopy(anawork))  objもコピーするのでダメ！
        ana.unregist_tmps()
        dpr(":::: anasrch: std: {}".format(ev))
        if len(ana_heap) < ANA_HEAPSIZE:
            heapq.heappush(ana_heap, storedata)
        else:
            heapq.heappushpop(ana_heap, storedata)
        return
    # 以下、dep>=0
    lse = analoop_stack[dep]  # lse: (chsuf, oblist)
    chsuf = lse[0]
    for ob in lse[1]:
        anawork[chsuf] = d.chunks[chsuf].ana = ob
        anasrch(dep-1, val)  # FIXME 照応の評価値があればここで足し込む
    anawork[chsuf] = d.chunks[chsuf].ana = None

def anasrch_root(pawsval):
    """ ana(の組)の候補の一つをセットしてanasrch()を呼ぶ """
    global analoop_stack, anawork
    n = len(d.chunks)
    analoop_stack = []
    anawork = [ None for k in range(n) ]
    for i in range(n):
        ch = d.chunks[i]
        if len(ana.ana_cands[i]) > 1:
            analoop_stack.append((i, ana.ana_cands[i]))  # (chsuf, oblist)
            anawork[i] = ch.ana = None
        elif len(ana.ana_cands[i]) == 1:
            anawork[i] = ch.ana = ana.ana_cands[i][0]
        else:
            assert len(ana.ana_cands[i]) == 0
            anawork[i] = ch.ana = None
    if DBG_DEPSRCH:
        print("**** anasrch_root anawk: ", anawork)
    anasrch(len(analoop_stack)-1, pawsval)

def anasrch_heap():
    """ dep/wsd/paaの結果を一つずつセットしてからanasrch_root()を呼ぶ """
    # paws_heapのエントリ: (val, depwork, wsdwork, paawork)
    global ana_heap, paws_heap, depwork, wsdwork, paawork
    n = len(d.chunks)
    ana.select_ana_cands(False)  # arg: noownobj
    ana_heap = []
    for heapent in paws_heap:
        val = heapent[0]
        for i in range(n):
            ch = d.chunks[i]
            if i < n-1:
                ch.depdst = heapent[1][i]  # 係り先文節#
            ch.wsd      = heapent[2][i]  # wsd意味番号
            ch.paasrces = heapent[3][i] # [ (srcch, case) ]
        depwork = heapent[1]
        wsdwork = heapent[2]
        paawork = heapent[3]
        if DBG_DEPSRCH:
            print("++++ anasrch_heap dep: ", depwork, "  wsd: ",
                  wsdwork, "  paa: ", paawork)
        #ana.toremove = []
        anasrch_root(val)
        #ana.unregist_tmps()
    if DBG_DEPSRCH:
        for anaent in ana_heap:
            print("/\/\ ana result: val:", anaent[0],
                  "\ndep: ", anaent[1], "\nwsd: ", anaent[2],
                  "\npaa: ", anaent[3], "\nana: ", anaent[4], "\n")
    # 一番いいのを選んで残す
    m = len(ana_heap)
    for k in range(m-1):
        heapq.heappop(ana_heap)

    heapent = ana_heap[0]
    val = heapent[0]
    dpr("&&&&&&&& best val: {}".format(val))
    for i in range(n):
        ch = d.chunks[i]
        if i < n-1:
            ch.depdst = heapent[1][i]  # 係り先文節#
        ch.wsd      = heapent[2][i]  # wsd意味番号
        ch.paasrces = heapent[3][i] # [ (srcch, case) ]
        # anaの解をセット  FIXME ここはanaでやるべきか
        if ch.maintyp not in [d.MainType.NOUN, d.MainType.NOUNDAPRED]:
            continue
        ch.ana = ana.ana_cands[0] if len(ana.ana_cands) == 1 else \
                               heapent[4][i]
    depwork = heapent[1]
    wsdwork = heapent[2]
    paawork = heapent[3]
    ana.toremove = []
    ana.anaeval(val)
    ana.apply_inference()
    if DBG_DEPSRCH:
        ana.stack_dump()


#### QA

def do_qa():
    # paws_heapはベストの一つだけ選ぶ  QAは曖昧性ないのが前提 (FIXME 甘い!)
    pawslen = len(paws_heap)
    for i in range(pawslen-1):
      heapq.heappop(paws_heap)

    heapent = paws_heap[0]  # そのベストを使う
    val = heapent[0]
    n = len(d.chunks)
    for i in range(n):
        ch = d.chunks[i]
        if i < n-1:
            ch.depdst = heapent[1][i]  # 係り先文節#
        ch.wsd      = heapent[2][i]  # wsd意味番号
        ch.paasrces = heapent[3][i] # [ (srcch, case) ]
    depwork = heapent[1]
    wsdwork = heapent[2]
    paawork = heapent[3]

    ana.ana_qa()


#### FIXME TBC zraも要る！
