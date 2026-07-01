def parse_ini(text):
    result={}; section=None
    for line in text.splitlines():
        line=line.strip()
        if not line or line[0] in ";#": continue
        if line.startswith("[") and line.endswith("]"):
            section=line[1:-1].strip(); result[section]={}
        elif "=" in line and section is not None:
            k,v=line.split("=",1); result[section][k.strip()]=v.strip()
    return result
