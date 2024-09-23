import pandas as pd
import plotly.graph_objects as go

chunk_size = 10000

positions = pd.DataFrame()

rows_count = 0
for chunk in pd.read_csv('matica/positions.csv', chunksize=chunk_size, header=None):
    positions = pd.concat([positions, chunk])
    rows_count += chunk_size
    print(f"Processing chunk {rows_count}, unique positions: {positions.shape}")
#    if rows_count > 50000:
#        break

# print(positions.head())
need_x = False
if need_x:
    fig_x = go.Figure(data=[go.Histogram(x=positions[0])])
    fig_x.update_layout(title='Histogram of x', xaxis_title='x', yaxis_title='Count')
    fig_x.show()

need_ident = False
if need_ident:
    x_ident_1 = positions[(positions[0] > 40) & (positions[0] < 70)]
    fix_xi1 = go.Figure(data=[go.Histogram(x=x_ident_1[0])])
    fix_xi1.update_layout(title='Histogram of x ident 1', xaxis_title='x', yaxis_title='Count')
    fix_xi1.show()

    x_ident_2 = positions[(positions[0] > 287) & (positions[0] < 287+30)]
    fix_xi2 = go.Figure(data=[go.Histogram(x=x_ident_2[0])])
    fix_xi2.update_layout(title='Histogram of x ident 2', xaxis_title='x', yaxis_title='Count')
    fix_xi2.show()

need_y = False
if need_y:
    fig_y = go.Figure(data=[go.Histogram(x=positions[1])])
    fig_y.update_layout(title='Histogram of y', xaxis_title='y', yaxis_title='Count')
    fig_y.show()

need_dy = True
if need_dy:
    dy_filtered = positions[(positions[3] > 0) & (positions[3] < 30)]
    fig_dy = go.Figure(data=[go.Histogram(x=dy_filtered[3])])
    fig_dy.update_layout(title='Histogram of dy', xaxis_title='dy', yaxis_title='Count')
    fig_dy.show()

need_new_lines = False
if need_new_lines:
    row_new_lines1 = positions[(positions[3] > 2) & (positions[0] < 100) & (positions[0] > 0)]
    fig_x_new_lines1 = go.Figure(data=[go.Histogram(x=row_new_lines1[0])])
    fig_x_new_lines1.update_layout(title='Histogram of x new lines', xaxis_title='x', yaxis_title='Count')
    fig_x_new_lines1.show()

    row_new_lines2 = positions[(positions[3] > 2) & (positions[0] < 310) & (positions[0] > 285)]
    fig_x_new_lines2 = go.Figure(data=[go.Histogram(x=row_new_lines2[0])])
    fig_x_new_lines2.update_layout(title='Histogram of x new lines', xaxis_title='x', yaxis_title='Count')
    fig_x_new_lines2.show()
