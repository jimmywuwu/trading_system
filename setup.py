from setuptools import setup, find_packages

setup(
    name="trading_system",
    version="0.1.0",
    description="A flexible trading system for strategy backtesting and live trading",
    author="Trading System Developer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "requests>=2.28.0",
        "websocket-client>=1.3.0",
        "pyyaml>=6.0",
        "pybit>=5.7.0",
        "matplotlib>=3.5.0",
        "plotly>=5.10.0",
        "pytest>=7.0.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ]
    },
    entry_points={
        "console_scripts": [
            "trading-system=trading_system.cli:main",
        ],
    },
)