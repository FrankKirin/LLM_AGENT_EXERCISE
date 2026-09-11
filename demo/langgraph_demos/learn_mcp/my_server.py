# fastMCP实现一个极简server
from fastmcp import FastMCP

mcp = FastMCP("demo")

@mcp.tool
def add(a:int, b:int) -> int:
    return a+b

@mcp.resource("config://app")
def app_config()->dict:
    return {"env": "dev"}


if __name__ == "__main__":
    mcp.run()
