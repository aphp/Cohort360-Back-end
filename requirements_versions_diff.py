

def show_diff(old, future):
    old_deps = dict([p.strip().split("==") for p in open(old).readlines()])
    future_deps = dict([p.strip().split("==") for p in open(future).readlines()])
    diff = [f"{p}=={v}" for p, v in future_deps.items() if p not in old_deps]
    for i, p in enumerate(diff):
        print(f"{i} - {p}")


if __name__ == '__main__':
    old_file = "requirements_old.txt"
    future_file = "requirements.txt"
    show_diff(old_file, future_file)

