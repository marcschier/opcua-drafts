#!/usr/bin/env python3
from __future__ import annotations
import ast, copy, json, os, re, xml.sax.saxutils as sx
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

UANS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
NS = "{" + UANS + "}"
TYPES_NS = "http://opcfoundation.org/UA/2008/02/Types.xsd"
SCENE_URI = "http://opcfoundation.org/UA/OpenUSD/Scene/"
BASE_URI = "http://opcfoundation.org/UA/"
HasComponent = "i=47"; HasProperty = "i=46"; Organizes = "i=35"; HasTypeDefinition = "i=40"; HasAddIn = "i=17604"
FolderType = "i=61"; PropertyType = "i=68"; ObjectsFolder = "i=85"
Boolean = "i=1"; SByte = "i=2"; Int32 = "i=6"; UInt32 = "i=7"; Int64 = "i=8"; Float = "i=10"; Double = "i=11"; String = "i=12"; NodeId_ = "i=17"; BaseDataType = "i=24"
S = lambda nid: f"ns=1;i={nid}"
I = lambda nid: f"ns=2;i={nid}"
TYPE_IDS = {"UsdStageType": S(1001), "UsdPrimType": S(1002), "UsdGeomXformType": S(1006), "UsdGeomScopeType": S(1007), "UsdGeomMeshType": S(1009), "UsdGeomCylinderType": S(1010), "UsdGeomSphereType": S(1011), "UsdGeomCubeType": S(1012), "UsdGeomConeType": S(1013), "UsdGeomCapsuleType": S(1014), "UsdShadeMaterialType": S(1015), "UsdShadeShaderType": S(1016), "UsdRelationshipType": S(1017), "UsdVariantSetType": S(1018), "UsdCompositionArcType": S(1019), "UsdApiSchemaType": S(1020), "UsdCollectionAPIType": S(1021), "UsdAttributeType": S(2001)}
PRIM_TYPE_BY_USD = {"Xform": "UsdGeomXformType", "Scope": "UsdGeomScopeType", "Mesh": "UsdGeomMeshType", "Cylinder": "UsdGeomCylinderType", "Sphere": "UsdGeomSphereType", "Cube": "UsdGeomCubeType", "Cone": "UsdGeomConeType", "Capsule": "UsdGeomCapsuleType", "Material": "UsdShadeMaterialType", "Shader": "UsdShadeShaderType"}
ENUM = {"Def": 0, "Over": 1, "Class": 2, "Varying": 0, "Uniform": 1, "Unspecified": 0, "Model": 1, "Group": 2, "Assembly": 3, "Component": 4, "Subcomponent": 5, "Explicit": 0, "Prepend": 1, "Append": 2, "Delete": 3, "Ordered": 4, "Reference": 0, "Payload": 1, "Inherit": 2, "Specialize": 3, "VariantSet": 4, "Sublayer": 5, "Instance": 6}
REV_ENUM = {v: k for k, v in ENUM.items()}

@dataclass
class Attribute:
    name: str; type_name: str; value: Any = None; variability: str = "Varying"; custom: bool = False; connections: list[str] = field(default_factory=list); live: bool = False
@dataclass
class Relationship:
    name: str; targets: list[str]; custom: bool = False
@dataclass
class CompositionArc:
    arc_kind: str; asset_path: str = ""; prim_path: str = ""; list_position: str = "Explicit"; variant_set: str = ""; variant_selection: str = ""
@dataclass
class ApiSchema:
    schema_name: str; expansion_rule: str = ""
@dataclass
class VariantSet:
    set_name: str; selection: str = ""
@dataclass
class Prim:
    name: str; type_name: str = ""; kind: str = "Unspecified"; specifier: str = "Def"; active: bool = True; instanceable: bool = False; documentation: str = ""
    attributes: list[Attribute] = field(default_factory=list); relationships: list[Relationship] = field(default_factory=list); children: list['Prim'] = field(default_factory=list)
    composition: list[CompositionArc] = field(default_factory=list); api_schemas: list[ApiSchema] = field(default_factory=list); variant_sets: list[VariantSet] = field(default_factory=list); parent: 'Prim|None' = field(default=None, repr=False)
    @property
    def path(self):
        p=[]; c=self
        while c: p.append(c.name); c=c.parent
        return "/" + "/".join(reversed(p))
    def find(self, path):
        if self.path == path: return self
        for ch in self.children:
            r = ch.find(path)
            if r: return r
        return None
@dataclass
class Stage:
    source: str; stage_name: str; default_prim: str = ""; up_axis: str = "Z"; meters_per_unit: float = 1.0; kilograms_per_unit: float|None = None; time_codes_per_second: float|None = None; start_time_code: float|None = None; end_time_code: float|None = None; documentation: str = ""; root_prims: list[Prim] = field(default_factory=list)
    def all_prims(self):
        out=[]
        def w(p):
            out.append(p)
            for c in p.children: w(c)
        for r in self.root_prims: w(r)
        return out
    def find(self, path):
        for r in self.root_prims:
            x = r.find(path)
            if x: return x
        return None

def _strip_comments(s):
    out=[]
    for line in s.splitlines():
        q=False; res=[]
        for ch in line:
            if ch == '"': q = not q
            if ch == "#" and not q: break
            res.append(ch)
        out.append("".join(res))
    return "\n".join(out)
def _parse_value(v):
    v=(v or "").strip().rstrip(",")
    if not v: return None
    if v.startswith("<") and v.endswith(">"): return v[1:-1]
    if v in ("true","false"): return v == "true"
    try: return ast.literal_eval(v)
    except Exception: pass
    if re.fullmatch(r"[-+]?\d+", v): return int(v)
    if re.fullmatch(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?", v): return float(v)
    return v.strip('"')
def _stage_meta(text):
    m = re.search(r"#usda\s+1\.0\s*\((.*?)\)\s*", text, re.S); meta={}
    if not m: return meta, text
    b=m.group(1); d=re.search(r'doc\s*=\s*"""(.*?)"""', b, re.S)
    if d: meta["doc"] = d.group(1).strip()
    for k in ("defaultPrim","upAxis"):
        x=re.search(rf'{k}\s*=\s*"([^"]*)"', b)
        if x: meta[k]=x.group(1)
    for k in ("metersPerUnit","kilogramsPerUnit","timeCodesPerSecond","startTimeCode","endTimeCode"):
        x=re.search(rf"{k}\s*=\s*([-+0-9.]+)", b)
        if x: meta[k]=float(x.group(1))
    return meta, text[m.end():]
def _prim_meta(lines):
    b="\n".join(lines); kind="Unspecified"; inst=False; apis=[]
    m=re.search(r'kind\s*=\s*"([^"]+)"', b)
    if m: kind=m.group(1).capitalize()
    m=re.search(r'instanceable\s*=\s*(true|false)', b)
    if m: inst=m.group(1)=="true"
    m=re.search(r'apiSchemas\s*=\s*(\[[^\]]*\])', b)
    if m:
        try: apis=list(ast.literal_eval(m.group(1)))
        except Exception: apis=[]
    return kind, inst, apis
def parse_usda(path, stage_name=None, apply_example_overlays=True):
    text=_strip_comments(open(path, encoding="utf-8").read()); meta, body=_stage_meta(text)
    st=Stage(path, stage_name or os.path.splitext(os.path.basename(path))[0], meta.get("defaultPrim",""), meta.get("upAxis","Z"), float(meta.get("metersPerUnit",1)), meta.get("kilogramsPerUnit"), meta.get("timeCodesPerSecond"), meta.get("startTimeCode"), meta.get("endTimeCode"), meta.get("doc",""))
    lines=[l.rstrip() for l in body.splitlines() if l.strip()]
    stack=[]; pending=None; inmeta=False; ml=[]
    prim_re=re.compile(r'\s*(def|over|class)\s+(?:(\w+)\s+)?"([^"]+)"\s*(\(?)')
    attr_re=re.compile(r'\s*(custom\s+)?(uniform\s+)?([\w:\[\]]+)\s+([\w:]+)(\.connect)?\s*(?:=\s*(.*))?$')
    rel_re=re.compile(r'\s*(custom\s+)?rel\s+([\w:]+)\s*=\s*(.*)$')
    for ln in lines:
        if pending and inmeta:
            if ")" in ln:
                ml.append(ln.split(")",1)[0]); inmeta=False
                pending.kind,pending.instanceable,apis=_prim_meta(ml); pending.api_schemas=[ApiSchema(a) for a in apis]; ml=[]
                if "{" in ln: (stack[-1].children if stack else st.root_prims).append(pending); pending.parent=stack[-1] if stack else None; stack.append(pending); pending=None
                continue
            ml.append(ln); continue
        m=prim_re.match(ln)
        if m:
            spec, typ, name, par = m.groups(); pending=Prim(name, typ or "", specifier={"def":"Def","over":"Over","class":"Class"}[spec])
            if par or "(" in ln:
                after=ln.split("(",1)[1]
                if ")" in after:
                    ml=[after.split(")",1)[0]]; pending.kind,pending.instanceable,apis=_prim_meta(ml); pending.api_schemas=[ApiSchema(a) for a in apis]; ml=[]
                    if "{" in ln: (stack[-1].children if stack else st.root_prims).append(pending); pending.parent=stack[-1] if stack else None; stack.append(pending); pending=None
                else: inmeta=True; ml=[after]
            elif "{" in ln: (stack[-1].children if stack else st.root_prims).append(pending); pending.parent=stack[-1] if stack else None; stack.append(pending); pending=None
            continue
        if pending and "{" in ln:
            (stack[-1].children if stack else st.root_prims).append(pending); pending.parent=stack[-1] if stack else None; stack.append(pending); pending=None; continue
        if "}" in ln:
            for _ in range(ln.count("}")):
                if stack: stack.pop()
            continue
        if not stack: continue
        cur=stack[-1]; mr=rel_re.match(ln)
        if mr:
            custom,name,val=mr.groups(); v=_parse_value(val); cur.relationships.append(Relationship(name, [str(x) for x in (v if isinstance(v,list) else [v])], bool(custom))); continue
        ma=attr_re.match(ln)
        if ma:
            custom, uniform, typ, name, conn, val=ma.groups()
            cur.attributes.append(Attribute(name, typ, None if conn else _parse_value(val), "Uniform" if uniform else "Varying", bool(custom), [str(_parse_value(val))] if conn else []))
    if apply_example_overlays: _apply_overlays(st)
    return st
def _clone(p,parent=None):
    q=copy.deepcopy(p); q.parent=parent
    def f(x):
        for c in x.children: c.parent=x; f(c)
    f(q); return q
def _merge(dst, src):
    dst.attributes += copy.deepcopy(src.attributes); dst.relationships += copy.deepcopy(src.relationships); dst.api_schemas += copy.deepcopy(src.api_schemas)
    for c in src.children: dst.children.append(_clone(c,dst))
def _apply_overlays(st):
    b=os.path.basename(st.source).lower(); d=os.path.dirname(st.source)
    if b == "plant.usda":
        p=st.find("/Plant/Pumps/P101")
        if p:
            p.composition += [CompositionArc("Reference","pump.usda","/Pump","Append"), CompositionArc("Instance","pump.usda","/Pump","Append")]
        imp=st.find("/Plant/Pumps/P101/Impeller")
        if imp:
            for a in imp.attributes:
                if a.name=="xformOp:rotateZ": a.live=True; a.variability="Varying"
    if b == "cell.usda":
        rp=os.path.join(d,"robot.usda"); tp=os.path.join(d,"tool.usda")
        if os.path.exists(rp):
            rob=parse_usda(rp,"RobotAsset",False).root_prims[0]
            for mpath in ("/Cell/Robots/R1","/Cell/Robots/R2"):
                m=st.find(mpath)
                if m:
                    _merge(m, rob); m.kind="Component"; m.composition += [CompositionArc("Reference","robot.usda","/Robot","Append"), CompositionArc("Instance","robot.usda","/Robot","Append")]
                    bp=st.find(mpath+"/Base")
                    if bp: bp.api_schemas.append(ApiSchema("CollectionAPI","expandPrims"))
                    for p in st.all_prims():
                        if p.path.startswith(mpath+"/Base") and re.search(r"/J[1-6]$", p.path):
                            for a in p.attributes:
                                if a.name.startswith("xformOp:rotate"): a.live=True
        if os.path.exists(tp):
            tool=parse_usda(tp,"ToolAsset",False).root_prims[0]; fl=st.find("/Cell/Robots/R1/Base/J1/J2/J3/J4/J5/J6/Flange")
            if fl:
                t=_clone(tool,fl); t.name="Tool"; t.composition.append(CompositionArc("Reference","tool.usda","/Gripper","Append")); fl.children.append(t)

def _flat(v):
    if isinstance(v, tuple): v=list(v)
    if isinstance(v, list):
        out=[]
        for x in v: out += _flat(x) if isinstance(x,(list,tuple)) else [x]
        return out
    return [v]
def sdf_mapping(t):
    arr=t.endswith("[]"); b=t[:-2] if arr else t
    vec={"float2":(Float,1,"2"),"float3":(Float,1,"3"),"float4":(Float,1,"4"),"double2":(Double,1,"2"),"double3":(Double,1,"3"),"double4":(Double,1,"4"),"int2":(Int32,1,"2"),"int3":(Int32,1,"3"),"int4":(Int32,1,"4"),"color3f":(Float,1,"3"),"normal3f":(Float,1,"3"),"point3f":(Float,1,"3"),"vector3f":(Float,1,"3"),"texCoord2f":(Float,1,"2"),"quatf":(Float,1,"4"),"quatd":(Double,1,"4"),"matrix4d":(Double,1,"16")}
    sc={"bool":Boolean,"uchar":SByte,"int":Int32,"int64":Int64,"uint":UInt32,"float":Float,"half":Float,"double":Double,"string":String,"token":S(3006),"asset":S(3007),"timecode":S(3008)}
    if b in vec:
        dt,r,d=vec[b]; return dt, r+(1 if arr else 0), d
    if b in sc: return sc[b], 1 if arr else -1, None
    return BaseDataType, -2 if arr else -1, None
def _value_xml(dt, val, tn=""):
    if val is None: return ""
    vals=_flat(val) if isinstance(val,(list,tuple)) or tn.endswith("[]") or re.search(r"\d|color|point|vector|normal|quat|matrix|texCoord", tn) else [val]
    num=dt in (Double,Float,Int32,UInt32,SByte,Int64,S(3008)) or isinstance(val, int)
    if len(vals)>1 or isinstance(val,(list,tuple)) or tn.endswith("[]"):
        if num:
            tag={Double:"Double",Float:"Float",Int32:"Int32",UInt32:"UInt32",SByte:"SByte",Int64:"Int64",S(3008):"Double"}.get(dt, "Int32")
            return f'<Value><uax:ListOf{tag} xmlns:uax="{TYPES_NS}">' + "".join(f"<uax:{tag}>{x}</uax:{tag}>" for x in vals) + f"</uax:ListOf{tag}></Value>"
        return f'<Value><uax:ListOfString xmlns:uax="{TYPES_NS}">' + "".join(f"<uax:String>{sx.escape(str(x))}</uax:String>" for x in vals) + "</uax:ListOfString></Value>"
    v=vals[0]
    if dt == Boolean: return f'<Value><uax:Boolean xmlns:uax="{TYPES_NS}">{str(bool(v)).lower()}</uax:Boolean></Value>'
    if num:
        tag={Double:"Double",Float:"Float",Int32:"Int32",UInt32:"UInt32",SByte:"SByte",Int64:"Int64",S(3008):"Double"}.get(dt, "Int32")
        return f'<Value><uax:{tag} xmlns:uax="{TYPES_NS}">{v}</uax:{tag}></Value>'
    return f'<Value><uax:String xmlns:uax="{TYPES_NS}">{sx.escape(str(v))}</uax:String></Value>'

class Node:
    def __init__(self,nid,cls,bn,td=None,parent=None,dt=None,vr=None,dims=None,val=None,attrs=None):
        self.nid=nid; self.cls=cls; self.bn=bn; self.td=td; self.parent=parent; self.dt=dt; self.vr=vr; self.dims=dims; self.val=val; self.attrs=attrs or {}; self.refs=[]
def emit_nodeset(st, namespace):
    nodes=[]; nxt=[5000]; by={}
    def new(cls,bn,td=None,parent=None,dt=None,vr=None,dims=None,val=None,attrs=None,reftype=HasComponent):
        nxt[0]+=1; n=Node(nxt[0],cls,bn,td,parent,dt,vr,dims,val,attrs); nodes.append(n); by[I(n.nid)]=n
        if parent: n.refs.append((reftype,parent,False))
        if td: n.refs.append((HasTypeDefinition,td,True))
        return n
    def prop(parent,bn,dt,val,tn="",vr=-1,enum=False):
        if val is None or val=="": return
        n=new("UAVariable",bn,PropertyType,parent,dt,vr,None,_value_xml(dt,ENUM.get(val,val) if enum else val,tn),reftype=HasProperty); by[parent].refs.append((HasProperty,I(n.nid),True)); return n
    root=new("UAObject","OpenUSDScene",FolderType,ObjectsFolder,reftype=Organizes)
    stage=new("UAObject",st.stage_name,TYPE_IDS["UsdStageType"],I(root.nid)); root.refs.append((HasComponent,I(stage.nid),True))
    for bn,dt,val,tn in [("DefaultPrim",S(3006),st.default_prim,"token"),("UpAxis",S(3006),st.up_axis,"token"),("MetersPerUnit",Double,st.meters_per_unit,"double"),("KilogramsPerUnit",Double,st.kilograms_per_unit,"double"),("TimeCodesPerSecond",Double,st.time_codes_per_second,"double"),("StartTimeCode",S(3008),st.start_time_code,"timecode"),("EndTimeCode",S(3008),st.end_time_code,"timecode"),("RootLayerIdentifier",String,os.path.basename(st.source),"string"),("Documentation",String,st.documentation,"string")]: prop(I(stage.nid),bn,dt,val,tn)
    def add_prim(p,parent):
        td=TYPE_IDS.get(PRIM_TYPE_BY_USD.get(p.type_name,""),TYPE_IDS["UsdPrimType"]); pn=new("UAObject",p.name,td,I(parent.nid)); parent.refs.append((HasComponent,I(pn.nid),True))
        prop(I(pn.nid),"Specifier",S(3001),p.specifier,enum=True); prop(I(pn.nid),"TypeName",S(3006),p.type_name,"token"); prop(I(pn.nid),"Kind",S(3003),p.kind,enum=True); prop(I(pn.nid),"Active",Boolean,p.active,"bool"); prop(I(pn.nid),"Instanceable",Boolean,p.instanceable,"bool")
        folders={}
        for nm in ("AppliedSchemas","Composition","VariantSets","Metadata"):
            f=new("UAObject",nm,FolderType,I(pn.nid)); pn.refs.append((HasComponent,I(f.nid),True)); folders[nm]=f
        for api in p.api_schemas:
            an=new("UAObject",api.schema_name,TYPE_IDS["UsdCollectionAPIType"] if api.schema_name=="CollectionAPI" else TYPE_IDS["UsdApiSchemaType"],I(folders["AppliedSchemas"].nid),reftype=HasAddIn); folders["AppliedSchemas"].refs.append((HasAddIn,I(an.nid),True)); prop(I(an.nid),"SchemaName",S(3006),api.schema_name,"token"); prop(I(an.nid),"ExpansionRule",S(3006),api.expansion_rule,"token")
        for arc in p.composition:
            ar=new("UAObject",arc.arc_kind,TYPE_IDS["UsdCompositionArcType"],I(folders["Composition"].nid)); folders["Composition"].refs.append((HasComponent,I(ar.nid),True)); prop(I(ar.nid),"ArcKind",S(3005),arc.arc_kind,enum=True); prop(I(ar.nid),"AssetPath",S(3007),arc.asset_path,"asset"); prop(I(ar.nid),"PrimPath",String,arc.prim_path,"string"); prop(I(ar.nid),"ListPosition",S(3004),arc.list_position,enum=True)
        for vs in p.variant_sets:
            vn=new("UAObject",vs.set_name,TYPE_IDS["UsdVariantSetType"],I(folders["VariantSets"].nid)); folders["VariantSets"].refs.append((HasComponent,I(vn.nid),True)); prop(I(vn.nid),"SetName",String,vs.set_name,"string"); prop(I(vn.nid),"Selection",S(3006),vs.selection,"token")
        for a in p.attributes:
            dt,vr,d=sdf_mapping(a.type_name); av=new("UAVariable",a.name,TYPE_IDS["UsdAttributeType"],I(pn.nid),dt,vr,d,_value_xml(dt,a.value,a.type_name),{"AccessLevel":"3","UserAccessLevel":"3","Historizing":"true"} if a.live else {}); pn.refs.append((HasComponent,I(av.nid),True))
            ns=a.name.split(":")[0] if ":" in a.name else ""; prop(I(av.nid),"UsdTypeName",S(3006),a.type_name,"token"); prop(I(av.nid),"Variability",S(3002),a.variability,enum=True); prop(I(av.nid),"Custom",Boolean,a.custom,"bool"); prop(I(av.nid),"Namespace",S(3006),ns,"token")
        for r in p.relationships:
            rn=new("UAObject",r.name,TYPE_IDS["UsdRelationshipType"],I(pn.nid)); pn.refs.append((HasComponent,I(rn.nid),True)); prop(I(rn.nid),"Custom",Boolean,r.custom,"bool"); prop(I(rn.nid),"TargetPaths",String,r.targets,"string[]",1)
        for c in p.children: add_prim(c,pn)
    for r in st.root_prims: add_prim(r,stage)
    aliases=[("Boolean",Boolean),("Int32",Int32),("UInt32",UInt32),("Int64",Int64),("Float",Float),("Double",Double),("String",String),("NodeId",NodeId_),("BaseDataType",BaseDataType),("HasComponent",HasComponent),("HasProperty",HasProperty),("Organizes",Organizes),("HasTypeDefinition",HasTypeDefinition),("HasAddIn",HasAddIn)]
    amap=dict(aliases); fmt=lambda x: amap.get(x,x)
    def enode(n):
        a=[f'{n.cls} NodeId="{I(n.nid)}"',f'BrowseName="2:{sx.escape(n.bn)}"']
        if n.parent: a.append(f'ParentNodeId="{n.parent}"')
        if n.dt: a.append(f'DataType="{fmt(n.dt)}"')
        if n.vr is not None: a.append(f'ValueRank="{n.vr}"')
        if n.dims: a.append(f'ArrayDimensions="{n.dims}"')
        for k,v in sorted(n.attrs.items()): a.append(f'{k}="{v}"')
        out=["  <"+" ".join(a)+">",f"    <DisplayName>{sx.escape(n.bn)}</DisplayName>","    <References>"]
        pr={HasTypeDefinition:0,HasProperty:1,HasComponent:2,Organizes:2,HasAddIn:2}
        for rt,tg,fw in sorted(n.refs,key=lambda x:(pr.get(x[0],3),x[0],x[1])):
            out.append(f'      <Reference ReferenceType="{fmt(rt)}"' + ("" if fw else ' IsForward="false"') + f'>{tg}</Reference>')
        out.append("    </References>")
        if n.val: out.append("    "+n.val)
        out.append(f"  </{n.cls}>"); return "\n".join(out)
    out=['<?xml version="1.0" encoding="utf-8"?>','<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">','  <NamespaceUris>',f'    <Uri>{SCENE_URI}</Uri>',f'    <Uri>{namespace}</Uri>','  </NamespaceUris>','  <Models>',f'    <Model ModelUri="{namespace}" Version="0.1.0" PublicationDate="2026-07-21T00:00:00Z">','      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="1.05.04" PublicationDate="2023-12-15T00:00:00Z" />',f'      <RequiredModel ModelUri="{SCENE_URI}" Version="0.1.0" PublicationDate="2026-07-21T00:00:00Z" />','    </Model>','  </Models>','  <Aliases>']
    out += [f'    <Alias Alias="{a}">{v}</Alias>' for a,v in aliases] + ['  </Aliases>'] + [enode(n) for n in nodes] + ['</UANodeSet>']
    return "\n".join(out)+"\n"

def _bn(e): return e.get("BrowseName","").split(":",1)[-1]
def _refs(e): return e.findall(f"{NS}References/{NS}Reference")
def _td(e):
    for r in _refs(e):
        if r.get("ReferenceType") in ("HasTypeDefinition", HasTypeDefinition): return (r.text or "").strip()
    return ""
def _val(e):
    v=e.find(f"{NS}Value")
    if v is None or len(v)==0: return None
    c=list(v)[0]; tag=c.tag.split("}",1)[-1]
    if tag.startswith("ListOf"):
        out=[]
        for x in list(c):
            t=x.tag.split("}",1)[-1]; s=x.text or ""
            out.append(float(s) if t in ("Double","Float") else int(s) if t.startswith("Int") or t in ("UInt32","SByte") else s)
        return out
    s=c.text or ""
    return s.lower()=="true" if tag=="Boolean" else float(s) if tag in ("Double","Float") else int(s) if tag.startswith("Int") or tag in ("UInt32","SByte") else s
def read_nodeset(path):
    root=ET.parse(path).getroot(); elems=[e for e in root if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")]; children={}
    for e in elems:
        if e.get("ParentNodeId"): children.setdefault(e.get("ParentNodeId"),[]).append(e)
    stage_el=next(e for e in elems if _td(e)==TYPE_IDS["UsdStageType"]); st=Stage(path,_bn(stage_el))
    def props(e): return {_bn(c): _val(c) for c in children.get(e.get("NodeId"),[]) if c.tag.endswith("UAVariable") and _td(c)==PropertyType}
    sp=props(stage_el); st.default_prim=sp.get("DefaultPrim",""); st.up_axis=sp.get("UpAxis","Z"); st.meters_per_unit=sp.get("MetersPerUnit",1.0)
    rev_type={v:k for k,v in TYPE_IDS.items()}; usd_by_scene={v:k for k,v in PRIM_TYPE_BY_USD.items()}
    spec_enum={0:"Def",1:"Over",2:"Class"}; var_enum={0:"Varying",1:"Uniform"}; kind_enum={0:"Unspecified",1:"Model",2:"Group",3:"Assembly",4:"Component",5:"Subcomponent"}; arc_enum={0:"Reference",1:"Payload",2:"Inherit",3:"Specialize",4:"VariantSet",5:"Sublayer",6:"Instance"}; list_enum={0:"Explicit",1:"Prepend",2:"Append",3:"Delete",4:"Ordered"}
    def rp(e,parent=None):
        pp=props(e); p=Prim(_bn(e), usd_by_scene.get(rev_type.get(_td(e),""), pp.get("TypeName","") or ""), kind_enum.get(pp.get("Kind"),"Unspecified"), spec_enum.get(pp.get("Specifier"),"Def"), bool(pp.get("Active",True)), bool(pp.get("Instanceable",False)), parent=parent)
        for c in children.get(e.get("NodeId"),[]):
            td=_td(c)
            if td==TYPE_IDS["UsdAttributeType"]:
                ap=props(c); p.attributes.append(Attribute(_bn(c), ap.get("UsdTypeName",""), _val(c), var_enum.get(ap.get("Variability"),"Varying"), bool(ap.get("Custom",False)), live=(c.get("Historizing")=="true")))
            elif td==TYPE_IDS["UsdRelationshipType"]:
                rp0=props(c); p.relationships.append(Relationship(_bn(c), rp0.get("TargetPaths") or [], bool(rp0.get("Custom",False))))
            elif td==FolderType and _bn(c)=="AppliedSchemas":
                for a in children.get(c.get("NodeId"),[]):
                    if _td(a) in (TYPE_IDS["UsdApiSchemaType"],TYPE_IDS["UsdCollectionAPIType"]):
                        ap=props(a); p.api_schemas.append(ApiSchema(ap.get("SchemaName") or _bn(a), ap.get("ExpansionRule","") or ""))
            elif td==FolderType and _bn(c)=="Composition":
                for a in children.get(c.get("NodeId"),[]):
                    if _td(a)==TYPE_IDS["UsdCompositionArcType"]:
                        ap=props(a); p.composition.append(CompositionArc(arc_enum.get(ap.get("ArcKind"),"Reference"), ap.get("AssetPath","") or "", ap.get("PrimPath","") or "", list_enum.get(ap.get("ListPosition"),"Explicit")))
            elif td in TYPE_IDS.values() and td not in (TYPE_IDS["UsdAttributeType"],TYPE_IDS["UsdRelationshipType"],TYPE_IDS["UsdCompositionArcType"],TYPE_IDS["UsdApiSchemaType"],TYPE_IDS["UsdCollectionAPIType"],TYPE_IDS["UsdVariantSetType"]):
                p.children.append(rp(c,p))
        return p
    for c in children.get(stage_el.get("NodeId"),[]):
        if _td(c) in TYPE_IDS.values() and _td(c) != TYPE_IDS["UsdAttributeType"]: st.root_prims.append(rp(c,None))
    return st
def _usd_val(v,tn):
    if v is None: return ""
    if isinstance(v,str): return f'"{v}"' if tn in ("token","asset","string") or tn.endswith("[]") else v
    if isinstance(v,bool): return "true" if v else "false"
    if isinstance(v,list):
        b=tn[:-2] if tn.endswith("[]") else tn
        if b in ("color3f","float3","double3","int3") and len(v)%3==0:
            groups=[v[i:i+3] for i in range(0,len(v),3)]
            return "["+", ".join("("+", ".join(str(x) for x in g)+")" for g in groups)+"]" if tn.endswith("[]") else "("+", ".join(str(x) for x in v)+")"
        return "["+", ".join(f'"{x}"' if isinstance(x,str) else str(x) for x in v)+"]"
    return str(v)
def write_usda(st,path):
    lines=["#usda 1.0","(",f'    defaultPrim = "{st.default_prim}"',f"    metersPerUnit = {st.meters_per_unit}",f'    upAxis = "{st.up_axis}"',")",""]
    def ep(p,ind=0):
        s={"Def":"def","Over":"over","Class":"class"}.get(p.specifier,"def"); typ=(p.type_name+" ") if p.type_name else ""; pad="    "*ind
        lines.append(f'{pad}{s} {typ}"{p.name}"' + (" (" if p.kind!="Unspecified" or p.api_schemas else ""))
        if p.kind!="Unspecified" or p.api_schemas:
            if p.kind!="Unspecified": lines.append(f'{pad}    kind = "{p.kind.lower()}"')
            if p.api_schemas: lines.append((f'{pad}    prepend apiSchemas = {[a.schema_name for a in p.api_schemas]}').replace("'","\""))
            lines.append(f"{pad})")
        lines.append(pad+"{")
        for a in p.attributes:
            pre=("custom " if a.custom else "") + ("uniform " if a.variability=="Uniform" else "")
            if a.connections: lines.append(f"{pad}    {pre}{a.type_name} {a.name}.connect = <{a.connections[0]}>")
            else: lines.append(f"{pad}    {pre}{a.type_name} {a.name} = {_usd_val(a.value,a.type_name)}")
        for r in p.relationships: lines.append(f"{pad}    rel {r.name} = <{r.targets[0]}>")
        for c in p.children: ep(c,ind+1)
        lines.append(pad+"}")
    for r in st.root_prims: ep(r,0)
    open(path,"w",encoding="utf-8",newline="\n").write("\n".join(lines)+"\n")
def _norm(v):
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, tuple): return [_norm(x) for x in v]
    if isinstance(v, list): return [_norm(x) for x in v]
    return v
def scene_signature(st):
    return [(p.path,p.type_name,p.kind,p.specifier,sorted((a.name,a.type_name,json.dumps(_norm(a.value),sort_keys=True),a.variability,a.custom) for a in p.attributes),sorted((r.name,tuple(r.targets)) for r in p.relationships)) for p in sorted(st.all_prims(),key=lambda p:p.path)]
