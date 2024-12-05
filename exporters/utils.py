from pathlib import Path

import yaml


def build_yaml(dict_in: dict, outfile_path: str | Path) -> bool:
    with open(outfile_path, 'w') as yaml_file:
        yaml.dump(dict_in,
                  yaml_file,
                  default_flow_style=False,
                  sort_keys=False)
    return True
