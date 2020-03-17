#!/usr/bin/env python3
"""interactive plot for SAtrace"""
import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import numpy as np
import plotly.graph_objs as go
from SAtraceWatchdog.watchgraph import read_conf, read_trace, title_renamer

EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)

app.layout = html.Div(
    [
        # File upload bunner
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ',
                               html.A('Select Files')]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True),
        html.Div(id='the_graph'),
        html.Div(id='output-data-upload'),
    ], )


def data_graph(df, filename):
    """アップロードされたデータのグラフを描画"""
    title = title_renamer(filename)
    yaxis_name = '受信電力[dBm]'

    def args(i):
        """graph_objs helper func"""
        return {'x': df.index, 'y': df[i], 'name': i}

    # チャートの種類をディクショナリで分岐
    # 内包表記でdfの列の数だけトレース
    data = [go.Scatter(args(i)) for i in df.columns]

    layout = go.Layout(title=go.layout.Title(text=title),
                       xaxis={
                           'type': 'linear',
                           'title': df.index.name,
                           'rangeslider': dict(visible=False),
                       },
                       yaxis={
                           'type': 'linear',
                           'title': yaxis_name,
                       },
                       margin={
                           'l': 60,
                           'b': 50
                       },
                       hovermode='closest')
    return dcc.Graph(id='the_graph', figure={'data': data, 'layout': layout})


def data_table(df):
    """アップロードされたデータの表を描画"""
    df.reset_index(inplace=True)  # indexもテーブルに含めるため
    data = df.to_dict('records')
    columns = [{'name': _i, 'id': _i} for _i in df.columns]
    return dash_table.DataTable(data=data, columns=columns)


def parse_contents(contents, filename, date):
    """drop & dropされたファイルの内容を読み込む"""
    _content_type, content_string = contents.split(',')

    # ファイルの内容読み取り
    decoded = base64.b64decode(content_string)
    # config読み取り
    first_line = decoded[:decoded.find(b'\n')]
    config = read_conf(first_line.decode())
    # data読み取り
    try:
        if filename[-4:] == '.txt':
            # Assume that the user uploaded a CSV file
            df = read_trace(io.StringIO(decoded.decode()), config)
            # 送信側bug -999を隠す
            df.replace(-999.9, np.nan, inplace=True)
            # グラフ装飾
        # """あとでpngをD&Dしたらtxtに名前を変えてtxt探してプロットする機能をつける"""
        # elif 'png' in filename:
        #     # Assume that the user uploaded an excel file
        #     df = pd.read_excel(io.BytesIO(decoded),
        #                        index_col=0,
        #                        parse_dates=True)
        else:
            raise ValueError
    except ValueError as e:
        print(e)
        return html.Div([f'There was an error processing this file.\n{e}'])

    return html.Div([
        data_graph(df, filename),
        html.H5(f'Filename: {filename}'),
        html.H5(f'Last update: {datetime.datetime.fromtimestamp(date)}'),
        data_table(df),
        html.Hr(),  # horizontal line

        # For debugging, display the raw contents provided by the web browser
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...',
                 style={
                     'whiteSpace': 'pre-wrap',
                     'wordBreak': 'break-all'
                 })
    ])


@app.callback(Output(
    'output-data-upload',
    'children',
), [
    Input('upload-data', 'contents'),
], [State('upload-data', 'filename'),
    State('upload-data', 'last_modified')])
def update_output(list_of_contents, list_of_names, list_of_dates):
    """ファイルをドロップしたときにコンテンツのアップデートを実行する"""
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8880)
