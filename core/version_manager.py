"""
灰度发布策略：
    1.按比例：1->5->20->50->100
    2.按用户：内部员工->白名单->全量
    3.蓝绿部署: 两套环境流量切换
设计思路：
    版本管理 + 回复路由
    1.按用户id哈希决定版本，固定用户固定版本
    2.白名单用户优先走灰度
    3.支持灰度转正和快速回滚
    4.版本健康度统计（请求数、错误率）
"""
import hashlib
from enum import Enum
from core.structured_logger import log_info
from core.config import settings

class VersionStatus(str, Enum):
    ACTIVE = "activate"
    CANARY = "canary"
    DEPRECATED = "deprecated"

class VersionInfo:
    def __init__(self, version: str, status: VersionStatus, canary_percent: int=0,
                 whitelist: list[str]=None, changelog: str=""):
        self.version = version
        self.status = status
        self.canary_percent = canary_percent
        self.whitelist = whitelist or []
        self.changelog = changelog
        self.request_count = 0
        self.error_count = 0

    # 获取错误率
    @property
    def error_rate(self):
        return self.error_count/self.request_count if self.request_count>0 else 0

class VersionManager:
    def __init__(self):
        self.versions: dict[str, VersionInfo] = {}  # {版本名：{版本信息}}
        self.activate_version: str | None = None
        self.canary_version: str | None = None

    def register_version(self, version: str, status: VersionStatus=VersionStatus.ACTIVE, canary_percent: int=0,
                         whitelist: list[str]=None, changelog: str=""):
        # 注册版本信息，并设置路由状态
        info = VersionInfo(version, status, canary_percent, whitelist, changelog)
        self.versions[version] = info

        # 根据状态更新version manager的active/canary版本信息
        if status == VersionStatus.ACTIVE:
            self.activate_version = version
        elif status == VersionStatus.CANARY:
            self.canary_version = version

        log_info("版本已注册", version=version, status=status.value)

    def get_version_for_user(self, user_id: str = None) -> str:
        # 方法1:白名单优先, 先看白名单
        if self.canary_version and user_id:
            canary = self.versions[self.canary_version]
            if user_id in canary.whitelist:
                return self.canary_version
        # 方法2: 按比例灰度(用户ID哈希取模)
        if self.canary_version and user_id:
            canary = self.versions[self.canary_version]
            if canary.canary_percent > 0:
                # hashlib.md5()处理字节数据
                # int("172abc", 16),一个16进制表示的数转为10进制数
                hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
                # canary_percent的用户给灰度版本
                if hash_val % 100 < canary.canary_percent:
                    return self.canary_version
        return self.activate_version

    def record_request(self, version: str, is_error: bool = False):
        """
        输入：
            版本号
        处理：
            判断version是否是个合法version；
            合法则：
                根据is_error值来决定是该版本号的request++还是error++
        输出：
            None
        """
        if version in self.versions:
            info = self.versions[version]
            info.request_count += 1
            if is_error:
                info.error_count += 1

    def get_version_health(self, version: str)-> dict:
        if version not in self.versions:
            return {}
        info = self.versions[version]
        return {
            "version": version, "status": info.status.value,
            "request_count": info.request_count, "error_count": info.error_count,
            "error_rate": round(info.error_rate * 100, 2),
            "canary_percent": info.canary_percent
        }

    def promote_canary(self):
        """灰度版本转正
        输入:
            None 
        处理:
            把版本中已有的active状态的版本给原来canary的版本
        输出:
            None
        """
        if not self.canary_version:
            return
        old = self.activate_version
        new = self.canary_version
        if old and old in self.versions:
            self.versions[old].status = VersionStatus.DEPRECATED
        self.versions[new].status = VersionStatus.ACTIVE
        self.versions[new].canary_percent = 0
        self.activate_version = new
        self.canary_version = None
        log_info("灰度转正", old_version=old, new_version=new)

    def rollback(self, version: str):
        """回滚到指定版本：当前ACTIVATE标记为DEPRECATED，目标版本设为ACTIVE"""
        # 元宝实现的版本
        if not self.activate_version:
            raise ValueError("当前没有活跃版本，无法回滚")

        target_info = self.versions.get(version)
        if not target_info:
            raise ValueError(f"目标版本{version}不存在，无法回滚")

        old_info = self.versions[self.activate_version]
        old_info.status = VersionStatus.DEPRECATED
        old_info.canary_percent = 0

        target_info.status = VersionStatus.ACTIVE
        target_info.canary_percent = 0
        self.activate_version = version

        if self.canary_version == version:
            self.canary_version = None

        log_info("版本已回滚", from_version=old_info.version, to_version=version)

    def update_canary_percent(self, percent: int):
        if self.canary_version:
            # min函数不能去掉，考虑调用方传了percent=150的情况
            self.versions[self.canary_version].canary_percent = max(0, min(100, percent))

version_manager = VersionManager()
version_manager.register_version(version=settings.version,
                                 status=VersionStatus.ACTIVE, changelog="初始版本")