[
    # Navigation escape
    "cd\\",
    "cd/",
    "cd ..",
    "pushd",
    "popd",

    # File write/copy/move outside sandbox
    "robocopy",

    # Deletion
    "erase",

    # Network / exfiltration
    "curl",
    "wget",
    "certutil",
    "bitsadmin",
    "ftp",
    "tftp",
    "net",
    "netsh",
    "nslookup",
    "ipconfig",

    # Execution
    "powershell",
    "pwsh",
    "cmd",
    "wscript",
    "cscript",
    "mshta",
    "rundll32",
    "regsvr32",
    "msiexec",
    "start",
    "call",
    "invoke",
    "explorer",
    "wmic",
    "at",
    "schtasks",

    # Registry
    "reg",
    "regedit",
    "regedt32",

    # User / privilege
    "net user",
    "net localgroup",
    "runas",
    "icacls",
    "cacls",
    "takeown",
    "whoami",

    # System info / reconnaissance
    "systeminfo",
    "tasklist",
    "taskkill",
    "sc",
    "services",
    "msconfig",
    "driverquery",
    "hostname",

    # Disk / volume
    "format",
    "diskpart",
    "chkdsk",
    "defrag",
    "mountvol",

    # Environment / shell tricks
    "set",
    "setx",
    "env",
    "path",

    # Encoding / obfuscation tools
    "certutil -encode",
    "certutil -decode",
    "makecab",
    "expand",
    "compact",

    # Redirection to outside sandbox
    ">",
    ">>",
    "2>",

    # Command chaining (can combine safe+dangerous)
    "&",
    "&&",
    "||",
    "|",

    # UNC paths
    "\\\\",

    # Environment variable expansion (hides paths)
    "%SYSTEMROOT%",
    "%WINDIR%",
    "%APPDATA%",
    "%USERPROFILE%",
    "%TEMP%",
    "%TMP%",
    "%PROGRAMFILES%",
    "%PROGRAMDATA%",
    "%COMSPEC%",
    "%PATH%",

    # Misc dangerous
    "clip",         # can exfiltrate to clipboard
    "assoc",        # file association tampering
    "ftype",        # file type tampering
    "shutdown",
    "logoff",
    "lock",
    "tsdiscon",
]
