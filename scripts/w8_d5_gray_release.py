"""
-版本注册
-灰度路由
-版本统计
-灰度转正
-版本回滚
-灰度比例调整
"""
from core.version_manager import VersionManager, VersionStatus
from core.logger import logger

def test_version_register():
    version_manager = VersionManager()
    version_manager.register_version("1.0.0", VersionStatus.ACTIVE, changelog="稳定版")
    version_manager.register_version("1.1.0", VersionStatus.CANARY, canary_percent=10,
                                     whitelist=["vip_1"], changelog="新功能")
    assert version_manager.activate_version == "1.0.0"
    assert version_manager.canary_version == "1.1.0"
    logger.info(f"主版本:{version_manager.activate_version}, 灰度：{version_manager.canary_version}")

def test_canary_routing():
    mgr = VersionManager()
    mgr.register_version("1.0.0", status=VersionStatus.ACTIVE)
    mgr.register_version("1.1.0", status=VersionStatus.CANARY, canary_percent=20, whitelist=["vip_1"])

    assert mgr.get_version_for_user("vip_1") == "1.1.0"
    logger.info("白名单用户走灰度")
    canary_count = sum(1 for i in range(1000) if mgr.get_version_for_user(f"u_{i}") == "1.1.0")
    percent = canary_count / 10
    logger.info(f"1000用户灰度占比{percent:.1f}")
    assert 15 < percent < 25, "没有达到15-25的百分比内"

    assert mgr.get_version_for_user(None) == "1.0.0"
    logger.info("匿名用户走主版本")

def test_version_statistics():
    mgr = VersionManager()
    mgr.register_version("1.0.0", status=VersionStatus.ACTIVE)
    for x in range(100):
        mgr.record_request("1.0.0", is_error=True)
    for x in range(105):
        mgr.record_request("1.0.0")
    health = mgr.get_version_health("1.0.0")
    logger.info(f"请求{health['request_count']}, 错误{health['error_count']}, 错误率{health['error_rate']}%")
    assert health["request_count"] == 205

def test_canary_promotion():
    mgr = VersionManager()
    mgr.register_version("1.0.0", VersionStatus.ACTIVE) # 会被标记为deperacated
    mgr.register_version("1.1.0", VersionStatus.CANARY, canary_percent=20)
    mgr.promote_canary()
    # 当前版本更新为正式版
    assert mgr.activate_version == "1.1.0"
    assert mgr.versions[mgr.activate_version].status == VersionStatus.ACTIVE
    # 当前canary百分比为0
    assert mgr.versions[mgr.activate_version].canary_percent == 0
    logger.info("canary_promotion测试通过")

def test_rollback():
    mgr = VersionManager()
    # 没有版本可以回滚
    # mgr.rollback(None)
    # assert ValueError("当前没有活跃版本，无法回滚")
    mgr.register_version("3.0.0", VersionStatus.ACTIVE)
    mgr.register_version("1.0.0", VersionStatus.DEPRECATED)
    # 测试从3.0.0版本回滚1.0.0
    mgr.rollback("1.0.0")
    assert mgr.activate_version == "1.0.0" and mgr.versions["1.0.0"].status==VersionStatus.ACTIVE
    logger.info("rollback测试通过")

def test_canary_percent():
    mgr = VersionManager()
    mgr.register_version("1.0.0", status=VersionStatus.ACTIVE)
    mgr.register_version("1.0.0", status=VersionStatus.CANARY, canary_percent=5)
    for p in [5, 20, 50, 100]:
        mgr.update_canary_percent(p)
        logger.info(f"版本中canary_percent比例:{mgr.versions['1.0.0'].canary_percent}")
    assert mgr.versions["1.0.0"].canary_percent == 100
    logger.info("灰度比例调整通过")

if __name__ == "__main__":
    # test_version_register()
    # test_canary_routing()
    # test_version_statistics()
    # test_canary_promotion()
    # test_rollback()
    test_canary_percent()
