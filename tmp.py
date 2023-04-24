input_file = 'input.txt' # 输入文件名
output_file = 'output.txt' # 输出文件名

with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        if not line.strip().startswith('#'):
            outfile.write(line)