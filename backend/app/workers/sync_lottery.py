"""同步体彩比赛到 daily_matches。运行：python -m app.workers.sync_lottery --days 7"""
import argparse

from app.infrastructure.database import database
from app.infrastructure.providers.lottery import LotteryProvider
from app.infrastructure.repositories import LotteryRepository


def sync(days: int) -> dict[str, int]:
    if not database.configured:
        raise RuntimeError('数据库未配置')
    matches = LotteryProvider().get_matches(days)
    result = LotteryRepository(database).save_matches(matches)
    return {'fetched': len(matches), **result}


def main() -> None:
    parser = argparse.ArgumentParser(description='同步体彩比赛数据')
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    print(sync(max(1, min(args.days, 7))))


if __name__ == '__main__':
    main()
