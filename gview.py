#!/usr/bin/env python3
"""interactive plot for SAtrace"""
import base64
import datetime
import io
import os
from collections import defaultdict

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from SAtraceWatchdog.watchgraph import read_conf

from SAtraceWatchdog.watchgraph import config_parse_freq

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


def title_renamer(filename: str) -> str:
    """ファイル名から %Y/%m/%d %T 形式の日付を返す"""
    basename = os.path.splitext(filename)[0]
    n = ''.join(basename.split('_', 1))
    return f'{n[:4]}/{n[4:6]}/{n[6:8]} {n[8:10]}:{n[10:12]}:{n[12:14]}'


def data_graph(
        df,
        filename,
):
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
    content_type, content_string = contents.split(',')

    # ファイルの内容読み取り
    decoded = base64.b64decode(content_string)
    # config読み取り
    first_line = decoded[:decoded.find(b'\n')]
    conf_dict = read_conf(first_line.decode())
    center_freq, _ = config_parse_freq(conf_dict, ':FREQ:CENT')
    span_freq, unit = config_parse_freq(conf_dict, ':FREQ:SPAN')
    points = int(conf_dict[':SWE:POIN'])
    # data読み取り
    try:
        if '.txt' == filename[-4:]:
            # Assume that the user uploaded a CSV file
            df = pd.read_table(
                io.StringIO(decoded.decode()),  # filename,
                sep='\s+',
                index_col=0,
                skiprows=1,
                skipfooter=1,
                names=[
                    conf_dict[':TRAC1:TYPE'], conf_dict[':TRAC2:TYPE'],
                    conf_dict[':TRAC3:TYPE']
                ],
                engine='python')
            # 送信側bug -999を隠す
            df.replace(-999.9, np.nan, inplace=True)
            # グラフ装飾
            df.index = np.linspace(center_freq - span_freq / 2,
                                   center_freq + span_freq / 2, points)
            df.index.name = unit
        """あとでpngをD&Dしたらtxtに名前を変えてtxt探してプロットする機能をつける"""
        # elif 'png' in filename:
        #     # Assume that the user uploaded an excel file
        #     df = pd.read_excel(io.BytesIO(decoded),
        #                        index_col=0,
        #                        parse_dates=True)
    except Exception as e:
        print(e)
        return html.Div([f'There was an error processing this file.\n{e}'])

    return html.Div([
        data_graph(df, filename),
        html.H5(f'filename: {filename}'),
        html.H5(f'last update: {datetime.datetime.fromtimestamp(date)}'),
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
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8880)
