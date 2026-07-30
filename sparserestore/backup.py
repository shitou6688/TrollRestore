from dataclasses import dataclass
from datetime import datetime
import plistlib
from pathlib import Path
from base64 import b64decode
from hashlib import sha1
from . import mbdb
from .mbdb import _FileMode
import os
_randbytes = getattr(__import__("random"), "randbytes", None) or os.urandom
from typing import Optional

DEFAULT = _FileMode.S_IRUSR | _FileMode.S_IWUSR | _FileMode.S_IXUSR | _FileMode.S_IRGRP | _FileMode.S_IXGRP | _FileMode.S_IROTH | _FileMode.S_IXOTH

@dataclass
class BackupFile:
    path: str
    domain: str

    def to_record(self):
        raise NotImplementedError()

@dataclass
class ConcreteFile(BackupFile):
    contents: bytes
    owner: int = 0
    group: int = 0
    inode: Optional[int] = None
    mode: _FileMode = DEFAULT

    def to_record(self):
        if self.inode is None:
            self.inode = int.from_bytes(_randbytes(8), "big")
        return mbdb.MbdbRecord(
            domain=self.domain,
            filename=self.path,
            link="",
            hash=sha1(self.contents).digest(),
            key=b"",
            mode=self.mode | _FileMode.S_IFREG,
            inode=self.inode,
            user_id=self.owner,
            group_id=self.group,
            mtime=int(datetime.now().timestamp()),
            atime=int(datetime.now().timestamp()),
            ctime=int(datetime.now().timestamp()),
            size=len(self.contents),
            flags=4,
            properties=[]
        )

@dataclass
class Directory(BackupFile):
    owner: int = 0
    group: int = 0
    mode: _FileMode = DEFAULT

    def to_record(self):
        return mbdb.MbdbRecord(
            domain=self.domain,
            filename=self.path,
            link="",
            hash=b"",
            key=b"",
            mode=self.mode | _FileMode.S_IFDIR,
            inode=0,
            user_id=self.owner,
            group_id=self.group,
            mtime=int(datetime.now().timestamp()),
            atime=int(datetime.now().timestamp()),
            ctime=int(datetime.now().timestamp()),
            size=0,
            flags=4,
            properties=[]
        )

@dataclass
class SymbolicLink(BackupFile):
    target: str
    owner: int = 0
    group: int = 0
    inode: Optional[int] = None
    mode: _FileMode = DEFAULT

    def to_record(self):
        if self.inode is None:
            self.inode = int.from_bytes(_randbytes(8), "big")
        return mbdb.MbdbRecord(
            domain=self.domain,
            filename=self.path,
            link=self.target,
            hash=b"",
            key=b"",
            mode=self.mode | _FileMode.S_IFLNK,
            inode=self.inode,
            user_id=self.owner,
            group_id=self.group,
            mtime=int(datetime.now().timestamp()),
            atime=int(datetime.now().timestamp()),
            ctime=int(datetime.now().timestamp()),
            size=0,
            flags=4,
            properties=[]
        )

@dataclass
class Backup:
    files: list
    device_info: dict = None  # 设备信息，用于生成兼容的 plist

    def write_to_directory(self, directory: Path):
        for file in self.files:
            if isinstance(file, ConcreteFile):
                with open(directory / sha1((file.domain + "-" + file.path).encode()).digest().hex(), "wb") as f:
                    f.write(file.contents)
            
        with open(directory / "Manifest.mbdb", "wb") as f:
            f.write(self.generate_manifest_db().to_bytes())
        with open(directory / "Status.plist", "wb") as f:
            f.write(self.generate_status())
        with open(directory / "Manifest.plist", "wb") as f:
            f.write(self.generate_manifest())
        with open(directory / "Info.plist", "wb") as f:
            f.write(plistlib.dumps({
            "Build Version": (self.device_info or {}).get("BuildVersion", "19A401"),
            "Device Name": "iPhone",
            "Display Name": "iPhone",
            "GUID": "00000000-0000-0000-0000-000000000000",
            "IMEI": "00",
            "Last Backup Date": datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
            "MEID": "",
            "Phone Number": "",
            "Product Name": "iPhone OS",
            "Product Type": (self.device_info or {}).get("ProductType", "iPhone10,1"),
            "Product Version": (self.device_info or {}).get("ProductVersion", "15.0"),
            "Serial Number": (self.device_info or {}).get("SerialNumber", ""),
            "Target Identifier": "00000000-0000-0000-0000-000000000000",
            "Target Type": "Device",
            "Unique Identifier": "00000000-0000-0000-0000-000000000000",
        }))

    def generate_manifest_db(self):
        records = []
        for file in self.files:
            records.append(file.to_record())
        return mbdb.Mbdb(records=records)
    
    def generate_status(self) -> bytes:
        return plistlib.dumps({
            "BackupState": "new",
            "Date": datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
            "IsFullBackup": False,
            "SnapshotState": "finished",
            "UUID": "00000000-0000-0000-0000-000000000000",
            "Version": "2.4"
        })
    
    def generate_manifest(self) -> bytes:
        # 使用设备实际信息，避免版本不匹配
        di = self.device_info or {}
        product_version = di.get("ProductVersion", "15.0")
        build_version = di.get("BuildVersion", "19A401")
        product_type = di.get("ProductType", "iPhone10,1")
        device_class = di.get("DeviceClass", "iPhone")
        serial = di.get("SerialNumber", "")
        udid = di.get("UniqueDeviceID", "00000000-0000-0000-0000-000000000000")

        # SystemDomainsVersion 根据系统版本映射
        pv = product_version.split(".")
        major = int(pv[0]) if pv else 15
        sd_versions = {14: "17.0", 15: "19.0", 16: "20.0"}
        sd_version = sd_versions.get(major, "20.0")

        return plistlib.dumps({
            "BackupKeyBag": b64decode("""
VkVSUwAAAAQAAAAFVFlQRQAAAAQAAAABVVVJRAAAABDud41d1b9NBICR1BH9JfVtSE1D
SwAAACgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAV1JBUAAA
AAQAAAAAU0FMVAAAABRY5Ne2bthGQ5rf4O3gikep1e6tZUlURVIAAAAEAAAnEFVVSUQA
AAAQB7R8awiGR9aba1UuVahGPENMQVMAAAAEAAAAAVdSQVAAAAAEAAAAAktUWVAAAAAE
AAAAAFdQS1kAAAAoN3kQAJloFg+ukEUY+v5P+dhc/Welw/oucsyS40UBh67ZHef5ZMk9
UVVVSUQAAAAQgd0cg0hSTgaxR3PVUbcEkUNMQVMAAAAEAAAAAldSQVAAAAAEAAAAAktU
WVAAAAAEAAAAAFdQS1kAAAAoMiQTXx0SJlyrGJzdKZQ+SfL124w+2Tf/3d1R2i9yNj9z
ZCHNJhnorVVVSUQAAAAQf7JFQiBNS12JDD7qwKNTSkNMQVMAAAAEAAAAA1dSQVAAAAAE
AAAAAktUWVAAAAAEAAAAAFdQS1kAAAAoSEelorROJA46ZUdwDHhMKiRguQyqHukotrxh
jIfqiZ5ESBXX9txi51VVSUQAAAAQfF0G/837QLq01xH9+66vx0NMQVMAAAAEAAAABFdS
QVAAAAAEAAAAAktUWVAAAAAEAAAAAFdQS1kAAAAol0BvFhd5bu4Hr75XqzNf4g0fMqZA
ie6OxI+x/pgm6Y95XW17N+ZIDVVVSUQAAAAQimkT2dp1QeadMu1KhJKNTUNMQVMAAAAE
AAAABVdSQVAAAAAEAAAAA0tUWVAAAAAEAAAAAFdQS1kAAAAo2N2DZarQ6GPoWRgTiy/t
djKArOqTaH0tPSG9KLbIjGTOcLodhx23xFVVSUQAAAAQQV37JVZHQFiKpoNiGmT6+ENM
QVMAAAAEAAAABldSQVAAAAAEAAAAA0tUWVAAAAAEAAAAAFdQS1kAAAAofe2QSvDC2cV7
Etk4fSBbgqDx5ne/z1VHwmJ6NdVrTyWi80Sy869DM1VVSUQAAAAQFzkdH+VgSOmTj3yE
cfWmMUNMQVMAAAAEAAAAB1dSQVAAAAAEAAAAA0tUWVAAAAAEAAAAAFdQS1kAAAAo7kLY
PQ/DnHBERGpaz37eyntIX/XzovsS0mpHW3SoHvrb9RBgOB+WblVVSUQAAAAQEBpgKOz9
Tni8F9kmSXd0sENMQVMAAAAEAAAACFdSQVAAAAAEAAAAA0tUWVAAAAAEAAAAAFdQS1kA
AAAo5mxVoyNFgPMzphYhm1VG8Fhsin/xX+r6mCd9gByF5SxeolAIT/ICF1VVSUQAAAAQ
rfKB2uPSQtWh82yx6w4BoUNMQVMAAAAEAAAACVdSQVAAAAAEAAAAA0tUWVAAAAAEAAAA
AFdQS1kAAAAo5iayZBwcRa1c1MMx7vh6lOYux3oDI/bdxFCW1WHCQR/Ub1MOv+QaYFVV
SUQAAAAQiLXvK3qvQza/mea5inss/0NMQVMAAAAEAAAACldSQVAAAAAEAAAAA0tUWVAA
AAAEAAAAAFdQS1kAAAAoD2wHX7KriEe1E31z7SQ7/+AVymcpARMYnQgegtZD0Mq2U55u
xwNr2FVVSUQAAAAQ/Q9feZxLS++qSe/a4emRRENMQVMAAAAEAAAAC1dSQVAAAAAEAAAA
A0tUWVAAAAAEAAAAAFdQS1kAAAAocYda2jyYzzSKggRPw/qgh6QPESlkZedgDUKpTr4Z
Z8FDgd7YoALY1g=="""),
            "Lockdown": {
                "DeviceName": "iPhone",
                "DeviceClass": device_class,
                "ProductType": product_type,
                "ProductVersion": product_version,
                "BuildVersion": build_version,
                "SerialNumber": serial,
                "UniqueDeviceID": udid,
            },
            "SystemDomainsVersion": sd_version,
            "Version": "9.1"
        })
