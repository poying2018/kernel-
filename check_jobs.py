import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f, encoding='utf-8-sig'))
    for job in d['jobs']:
        print(f"=== {job['name']} ({job['status']}) ===")
        for x in job['steps']:
            print(f"  {x['number']:2d}. {x['status']:12s} {str(x['conclusion']):12s} {x['name']}")
