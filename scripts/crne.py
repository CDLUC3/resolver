"""
Script for comparing resolved target for an ARK when using rslv, n2t, and ezid.

This is for diagnostic purposes to help ensure appropriate configuration
of rslv for ARK identifier resolution.

See also: https://hopper.rslv.xyz/ for viewing the redirect hops.
"""
import asyncio
import json
import logging
import sys
import click
import httpx

logging.basicConfig(level=logging.INFO)
L = logging.getLogger()
TIMEOUT = 30 #seconds


async def get_response(session, url):
    # TODO: terminate after some max bytes received
    response = await session.request(method="GET", url=url, follow_redirects=True, timeout=TIMEOUT)
    result = {
        "start": url,
        "final": str(response.url),
        "status": response.status_code
    }
    return result

async def do_work(ark):
    bases = [
        "https://n2t.net/{pid}",
        "https://rslv.xyz/{pid}",
        "https://ezid.cdlib.org/{pid}",
    ]
    urls = [base.format(pid=ark) for base in bases]
    session = httpx.AsyncClient()
    results = await asyncio.gather(*[get_response(session, url) for url in urls])
    await session.aclose()
    return results


@click.command()
@click.argument("ark")
def main(ark:str):
    results = asyncio.run(do_work(ark))
    results = {
        "input": ark,
        "N2T": results[0],
        "RSLV": results[1],
        "EZID": results[2]
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    sys.exit(main())
