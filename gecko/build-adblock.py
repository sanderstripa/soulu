"""Build a dynamic library from the unmodified CEF Rust blocker."""
import pathlib,shutil,subprocess,os,sys
root=pathlib.Path(__file__).resolve().parent.parent
source=root/'gecko-cache/adblock';source.parent.mkdir(exist_ok=True)
shutil.copytree(root/'cef/soulu/adblock',source,dirs_exist_ok=True,ignore=shutil.ignore_patterns('target'))
p=source/'Cargo.toml';p.write_text(p.read_text().replace('crate-type = ["staticlib"]','crate-type = ["staticlib", "cdylib"]'))
subprocess.run(['cargo','build','--release','--locked'],cwd=source,check=True)
name='soulu_adblock.dll' if os.name=='nt' else 'libsoulu_adblock.so'
target=root/(sys.argv[1] if len(sys.argv)>1 else 'gecko-out')/'runtime/soulu/adblock';target.mkdir(parents=True,exist_ok=True)
shutil.copy(source/'target/release'/name,target/name)
shutil.copytree(source/'notices',target/'notices',dirs_exist_ok=True)
shutil.copy(source/'LICENSE-MPL-2.0',target/'LICENSE-MPL-2.0')
