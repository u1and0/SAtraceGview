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
import pandas as pd
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


def data_graph(df, title):
    """アップロードされたデータのグラフを描画"""
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


def decode_contents(c):
    """ ファイルの内容読み取り"""
    _content_type, content_string = c.split(',')
    decoded = base64.b64decode(content_string)
    # config読み取り
    first_line = decoded[:decoded.find(b'\n')].decode()
    config = read_conf(first_line)
    data = io.StringIO(decoded.decode())
    return data, config


def parse_contents_multi(contents, filename, date):
    """複数ファイルdrop & dropされたファイルの内容を読み込む"""
    df = pd.DataFrame({
        title_renamer(f): read_trace(*decode_contents(c)).iloc[:, 2]
        for f, c in zip(filename, contents)
    })
    df.replace(-999.9, np.nan, inplace=True)  # 送信側bug -999を隠す
    return html.Div([
        data_graph(df, title=str(len(filename)) + ' files'),
        html.H5('Filename: {}'.format(' '.join(filename))),
        # html.H5(f'Last update: {datetime.datetime.fromtimestamp(date)}'),
        data_table(df),
    ])


def parse_contents(contents, filename, date):
    """drop & dropされたファイルの内容を読み込む"""
    # data読み取り
    df = read_trace(*decode_contents(contents))
    # 送信側bug -999を隠す
    df.replace(-999.9, np.nan, inplace=True)

    return html.Div([
        data_graph(df, title_renamer(filename)),
        html.H5(f'Filename: {filename}'),
        html.H5(f'Last update: {datetime.datetime.fromtimestamp(date)}'),
        data_table(df),
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
        try:  # txtファイル以外はエラー
            if not all(n[-4:] == '.txt' for n in list_of_names):
                raise ValueError
        except ValueError as e:
            print(e)
            return html.Div([f'There was an error processing this file.\n{e}'])

        if len(list_of_contents) > 1:
            return parse_contents_multi(
                list_of_contents,
                list_of_names,
                list_of_dates,
            )
        # list_of_contents is not None:
        return [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8880)
