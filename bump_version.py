"""Run once before building each new release: 1.9 becomes 2.0."""
from pathlib import Path
import re
p=Path(__file__).with_name('update_support.py')
s=p.read_text(encoding='utf8')
m=re.search(r"VERSION='(\d+)\.(\d+)'",s)
if not m:raise SystemExit('Invalid version')
major,minor=map(int,m.groups());minor+=1
if minor>=10:major+=1;minor=0
version=f'{major}.{minor}'
p.write_text(s[:m.start()]+f"VERSION='{version}'"+s[m.end():],encoding='utf8')
print('V'+version)
