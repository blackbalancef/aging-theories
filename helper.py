import pandas as pd


def get_all_results():
    # path = 'data_output'
    path = 'examples_output/'
    # return one big df


def file_reader(file_name):
    """Return dataframe of a specific file"""
    # path = 'data_output'
    path = 'examples_output/'
    # read a file from the folder
    df = pd.read_csv(path + file_name)
    return df


if __name__ == '__main__':
    file_name = 'aging_theories_papers_2025-10-22_00-45.csv'
    df = file_reader(file_name)
    print(df.info())
    print(df)