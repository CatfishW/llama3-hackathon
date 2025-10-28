import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8009,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()


