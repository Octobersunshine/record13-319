import time
from env_service import EnvService


def example_basic() -> None:
    env = EnvService()

    print("=" * 50)
    print("环境变量服务使用示例")
    print("=" * 50)

    print("\n1. 基础查询 (get/get_str):")
    print(f"   APP_NAME = {env.get_str('APP_NAME')}")
    print(f"   APP_ENV = {env.get('APP_ENV', 'production')}")
    print(f"   NOT_EXIST = {env.get('NOT_EXIST', '默认值')}")

    print("\n2. 类型转换查询:")
    print(f"   APP_PORT (int) = {env.get_int('APP_PORT')}")
    print(f"   APP_DEBUG (bool) = {env.get_bool('APP_DEBUG')}")
    print(f"   API_TIMEOUT (int) = {env.get_int('API_TIMEOUT')}")

    print("\n3. 批量前缀查询 (DB_):")
    db_config = env.get_prefix("DB")
    for key, value in db_config.items():
        print(f"   {key} = {value}")

    print("\n4. 批量前缀查询 (REDIS_):")
    redis_config = env.get_prefix("REDIS")
    for key, value in redis_config.items():
        print(f"   {key} = {value}")

    print("\n5. 检查是否存在:")
    print(f"   has('API_KEY') = {env.has('API_KEY')}")
    print(f"   has('NOT_EXIST') = {env.has('NOT_EXIST')}")

    print("\n6. 必填项查询:")
    try:
        api_key = env.require("API_KEY")
        print(f"   API_KEY = {api_key}")
    except KeyError as e:
        print(f"   {e}")

    print("\n7. 列表查询:")
    test_list = env.get_list("TEST_LIST", default=["a", "b", "c"])
    print(f"   TEST_LIST (默认值) = {test_list}")


def example_hot_reload() -> None:
    print("\n" + "=" * 50)
    print("热加载功能使用示例")
    print("=" * 50)

    env = EnvService()

    def on_config_change(new_vars):
        print(f"\n   🔔 配置已更新! APP_NAME = {new_vars.get('APP_NAME', 'N/A')}")

    print("\n8. 启动文件监控 (热加载):")
    env.start_watch(callback=on_config_change, debounce=0.5)
    print(f"   监控状态: {env.is_watching()}")

    print("\n   💡 提示: 修改项目根目录下的 .env 文件，")
    print("          系统会自动检测到变更并刷新配置。")

    print("\n9. 注册/注销变更监听器:")
    def another_callback(vars):
        pass
    env.on_change(another_callback)
    print("   已注册 another_callback")
    env.off_change(another_callback)
    print("   已注销 another_callback")

    print("\n10. 手动刷新 (reload):")
    env.reload()
    print("    已执行手动 reload()")

    print("\n11. 停止监控:")
    env.stop_watch()
    print(f"    监控状态: {env.is_watching()}")

    print("\n" + "=" * 50)
    print("示例运行完毕!")
    print("=" * 50)


if __name__ == "__main__":
    example_basic()
    example_hot_reload()
