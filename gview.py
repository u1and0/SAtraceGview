#!/usr/bin/env python3
"""interactive plot for SAtrace"""
import base64
import io
import numpy as np
import plotly.graph_objs as go
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from SAtraceWatchdog.tracer import read_conf, read_trace, title_renamer

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
        html.Div(id='preview-button'),
        html.Div(id='next-button'),
        html.Div(id='the_graph'),
        html.Div(id='output-data-upload'),
    ], )


def data_graph(df, title, yaxis_name=None):
    """アップロードされたデータのグラフを描画"""
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


def parse_contents_multi(contents, filename):
    """複数ファイルdrop & dropされたファイルの内容を読み込む"""
    # df = pd.DataFrame({
    #     title_renamer(f): read_trace(*decode_contents(c),
    #                                  usecols='AVER').squeeze()
    #     for f, c in zip(filename, contents)
    # })
    # df.replace(-999.9, np.nan, inplace=True)  # 送信側bug -999を隠す
    singlegraph = [
        html.Button(children='preview', id='prev-button', n_clicks=0),
        html.Button(children='next', id='next-button', n_clicks=0),
        parse_contents(contents[0], filename[0]),
    ]
    return html.Div(singlegraph)
    # return html.Div([
    #     html.Button(children='preview', id='prev-button'),
    #     html.Button(children='next', id='next-button'),
    #     data_graph(df, title='{len(filename)} files'),
    #     html.H5('Filename: {}'.format(' '.join(filename))),
    #     data_table(df),
    # ])


def parse_contents(contents, filename):
    """drop & dropされたファイルの内容を読み込む"""
    # data読み取り
    df = read_trace(*decode_contents(contents))
    # 送信側bug -999を隠す
    df.replace(-999.9, np.nan, inplace=True)

    return html.Div([
        data_graph(df, title_renamer(filename)),
        html.H5(f'Filename: {filename}'),
        data_table(df),
    ])


@app.callback(
    Output('the_graph', 'children'),
    [Input('next-button', 'n_clicks'),
     Input('preview-button', 'n_clicks')],
    [State('upload-data', 'contents'),
     State('upload-data', 'filename')])
def update_graph(prev_btn: int, next_btn: int, contents, filename):
    """preview / next ボタンが押されたときに、
    グラフを次のデータにアップデートする"""
    index = 0
    if not (prev_btn is None or next_btn is None):
        index = next_btn - prev_btn
    if not (contents is None and filename is None):
        return html.Div([
            html.Button(children='preview',
                        id='preview-button',
                        n_clicks=prev_btn),
            html.Button(children='next', id='next-button', n_clicks=next_btn),
            parse_contents(contents[index], filename[index]),
        ])


@app.callback(Output(
    'output-data-upload',
    'children',
), [
    Input('upload-data', 'contents'),
], [
    State('upload-data', 'filename'),
])
def update_output(list_of_contents, list_of_names):
    """ファイルをドロップしたときにコンテンツのアップデートを実行する"""
    if list_of_contents is not None:
        try:  # txtファイル以外はエラー
            if not all(n[-4:] == '.txt' for n in list_of_names):
                raise ValueError('txt形式のファイルがアップロードされませんでした。')
        except ValueError as e:
            print(e)
            return html.Div([f'{e}'])
        # if ... None: の下につかないとlist_of_contentsがNoneなので、エラー
        if len(list_of_contents) > 1:
            return parse_contents_multi(list_of_contents, list_of_names)
        return parse_contents(list_of_contents[0], list_of_names[0])


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8880)
