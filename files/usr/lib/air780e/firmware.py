"""Pinned optional ARM64 flashing runtime, isolated from OpenWrt system libraries."""
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

CACHE=Path('/tmp/air780e-firmware')
LUA=Path(__file__).parent/'firmware/lua'
ASSETS={
 'core.soc':('https://cdn18.luatos.com/files/Air780EHV/LuatOS_Air780EHV/LuatOS-SoC_V2052_Air780EHV/LuatOS-SoC_V2052_Air780EHV_1.soc','55cb7c2fe6d63caac4811f2ea58ac93ccf4fae678732e2f05903952c6d6e1d5f'),
 'cli.tar.gz':('https://github.com/wendal/luatos-cli/releases/download/v1.11.0/luatos-cli-aarch64-unknown-linux-gnu.tar.gz','14f1cd3888e1e201b04afedd48166c9e0f5ebe7597ef19634a0f051a3a8cdaf6'),
 'libc6.deb':('https://ports.ubuntu.com/pool/main/g/glibc/libc6_2.39-0ubuntu8_arm64.deb','04d7cb73e608b41713b63ef915577f7f5d75e95b1b33174e82e05687fdb6cfaf'),
 'libgcc-s1.deb':('https://ports.ubuntu.com/pool/main/g/gcc-14/libgcc-s1_14-20240412-0ubuntu1_arm64.deb','bb1c262f2ac9aeb357d3344a06f22f1057306694f6200896775a03ecced08b13'),
 'libudev1.deb':('https://ports.ubuntu.com/pool/main/s/systemd/libudev1_255.4-1ubuntu8_arm64.deb','62567062c6f08702d6876bd5ad8993ff618478df9bd8613270032e9477b82e93'),
 'libcap2.deb':('https://ports.ubuntu.com/pool/main/libc/libcap2/libcap2_2.66-5ubuntu2_arm64.deb','88c75467ee09a14981661782bf62f4a0029458922245d7f22225c2ca4441eeee')}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()

def fetch(name,progress):
    url,sha=ASSETS[name]
    path=CACHE/name
    if path.exists() and digest(path)==sha:return path
    part=CACHE/(name+'.part')
    progress('正在下载并校验 '+name)
    try:
        subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https',
            '--connect-timeout','15','--max-time','300','--retry','2','--output',str(part),url],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=930)
        if digest(part)!=sha:raise RuntimeError('下载文件校验失败，拒绝执行')
        os.replace(part,path)
    finally:part.unlink(missing_ok=True)
    return path

def deb_data(path):
    raw=path.read_bytes()
    if not raw.startswith(b'!<arch>\n'):raise RuntimeError('运行库压缩包格式不正确')
    offset=8
    while offset+60<=len(raw):
        header=raw[offset:offset+60];name=header[:16].decode().strip().rstrip('/')
        size=int(header[48:58]);data=raw[offset+60:offset+60+size]
        if len(data)!=size:raise RuntimeError('运行库压缩包不完整')
        if name.startswith('data.tar'):
            if name.endswith('.zst'):
                return subprocess.check_output(['zstd','-d','-q','-c'],input=data,timeout=20)
            return data
        offset+=60+size+(size%2)
    raise RuntimeError('运行库缺少数据归档')

def prepare(progress=lambda value:None,core=False):
    if platform.machine() not in ('aarch64','arm64'):raise RuntimeError('路由器内烧录目前只支持 ARM64；其他架构请使用原版 Mac 工具')
    CACHE.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(CACHE,0o700)
    if shutil.disk_usage(CACHE).free<40*1024*1024:raise RuntimeError('固件准备至少需要 40 MB 可用临时空间')
    lib=CACHE/'lib';lib.mkdir(exist_ok=True,mode=0o700)
    for name in ('libc6.deb','libgcc-s1.deb','libudev1.deb','libcap2.deb'):
        with tarfile.open(fileobj=io.BytesIO(deb_data(fetch(name,progress))),mode='r:*') as archive:
            for member in archive:
                basename=Path(member.name).name
                if not member.isfile():continue
                alias=None
                if basename in ('ld-linux-aarch64.so.1','libc.so.6','libm.so.6','libgcc_s.so.1'):alias=basename
                elif re.fullmatch(r'libudev\.so\.1(?:\.\d+)+',basename):alias='libudev.so.1'
                elif re.fullmatch(r'libcap\.so\.2(?:\.\d+)+',basename):alias='libcap.so.2'
                if alias:
                    if member.size>15*1024*1024:raise RuntimeError('运行库大小异常')
                    (lib/alias).write_bytes(archive.extractfile(member).read());(lib/alias).chmod(0o700)
    tool=CACHE/'luatos-cli'
    with tarfile.open(fetch('cli.tar.gz',progress),'r:gz') as archive:
        members=[m for m in archive if Path(m.name).name=='luatos-cli' and m.isfile()]
        if len(members)!=1:raise RuntimeError('烧录工具归档结构异常')
        tool.write_bytes(archive.extractfile(members[0]).read());tool.chmod(0o700)
    prefix=[str(lib/'ld-linux-aarch64.so.1'),'--library-path',str(lib),str(tool)]
    test=subprocess.run(prefix+['--version'],capture_output=True,text=True,timeout=10)
    if test.returncode:raise RuntimeError('烧录工具无法在此路由器运行：'+test.stderr[:300])
    if '1.11.0' not in test.stdout:raise RuntimeError('烧录工具版本不匹配')
    soc=fetch('core.soc',progress) if core else None
    if soc:
        progress('正在验证官方核心固件结构')
        metadata=json.loads(command(prefix,['soc','info',str(soc),'--format','json'],60))
        if metadata.get('status')!='ok' or metadata.get('data',{}).get('chip',{}).get('type')!='ec7xx':
            raise RuntimeError('固件结构校验失败')
        compile_scripts(prefix,progress)
        (CACHE/'ready.json').write_text(json.dumps({'tool':'1.11.0','coreSHA256':ASSETS['core.soc'][1]}))
    return prefix,soc

def compile_scripts(prefix, progress):
    """Run the pinned CLI's embedded compiler through the same private loader."""
    helpers=CACHE/'helpers';helpers.mkdir(exist_ok=True,mode=0o700)
    output=CACHE/'compiled';output.mkdir(exist_ok=True,mode=0o700)
    env=dict(os.environ,LUATOS_CLI_HELPER_CACHE=str(helpers))
    progress('正在编译并验证配套 Lua 脚本')
    # CLI extracts and verifies its embedded helper before trying execve.
    result=subprocess.run(prefix+['build','luac','--src',str(LUA),'--output',str(output),'--bitw','32'],
        env=env,capture_output=True,text=True,timeout=30)
    compilers=list(helpers.glob('luac32_helper-1.11.0-*'))
    compilers=[p for p in compilers if p.suffix!='.json' and p.is_file()]
    if len(compilers)!=1:raise RuntimeError('未能安全提取内置 Lua 编译器：'+result.stderr[-300:])
    compiler=compilers[0]
    metadata=json.loads(Path(str(compiler)+'.json').read_text())
    if metadata.get('sha256')!=digest(compiler):raise RuntimeError('内置 Lua 编译器校验失败')
    for source in sorted(LUA.glob('*.lua')):
        compiled=subprocess.run(prefix[:3]+[str(compiler),'@'+source.name,'99'],input=source.read_bytes(),capture_output=True,timeout=20)
        if compiled.returncode or not compiled.stdout.startswith(b'\x1bLua\x53'):
            raise RuntimeError('Lua 脚本编译失败：'+source.name)
        (output/(source.stem+'.luac')).write_bytes(compiled.stdout)
    return output

def devices():
    found={}
    for item in Path('/sys/class/tty').glob('ttyACM*'):
        interface=(item/'device').resolve();parent=interface.parent
        try:
            vid=(parent/'idVendor').read_text().strip()
            pid=(parent/'idProduct').read_text().strip()
            number=(interface/'bInterfaceNumber').read_text().strip()
            if vid in ('19d1','17d1') and pid=='0001':
                value=found.setdefault(str(parent),{'vendor':vid,'ports':[]})
                value['ports'].append((number,'/dev/'+item.name))
        except OSError:pass
    return list(found.values())

def single():
    found=devices()
    if len(found)!=1:raise RuntimeError('请只连接一台受支持模块；拒绝猜测烧录设备')
    return found[0]

def command(prefix,args,timeout):
    result=subprocess.run(prefix+args,capture_output=True,text=True,timeout=timeout)
    if result.returncode:
        text=re.sub(r'\b\d{12,22}\b','[设备标识已隐藏]',result.stdout+result.stderr)
        raise RuntimeError('烧录工具失败：'+text[-1000:])
    return result.stdout

def install(model,confirmation,progress=lambda value:None,close=lambda:None):
    if model!='Air780EHV_A11' or confirmation!='覆盖固件':raise ValueError('必须手工确认 Air780EHV_A11 型号及覆盖固件')
    single()
    if not all((LUA/name).is_file() for name in ('main.lua','sys.lua','sysplus.lua')):raise RuntimeError('配套脚本不完整')
    prefix,core=prepare(progress,core=True)
    compiled=CACHE/'compiled'
    # All downloads and validation complete before any device is changed.
    close();device=single()
    if device['vendor']=='19d1':
        ports=[p for i,p in device['ports'] if i=='02']
        if len(ports)!=1:raise RuntimeError('无法识别 SOC 控制口，取消烧录')
        progress('资源已校验，正在进入下载模式；请勿拔线')
        command(prefix,['device','boot','--chip','ec718','--port',ports[0]],30)
    deadline=time.monotonic()+35;port=None
    while time.monotonic()<deadline:
        found=devices()
        if len(found)>1:raise RuntimeError('出现多台模块，取消烧录')
        if len(found)==1 and found[0]['vendor']=='17d1' and len(found[0]['ports'])==1:
            port=found[0]['ports'][0][1];break
        time.sleep(.5)
    if not port:raise RuntimeError('未安全识别下载口，取消烧录')
    progress('正在写入固件与脚本，请勿断电或拔线')
    command(prefix,['flash','run','--soc',str(core),'--port',port,'--script',str(compiled)],600)
    progress('固件写入完成，正在重新验证设备协议')
    return '固件写入完成'
