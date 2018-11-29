from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


@app.route('/')
def home():
    # import packages to create candlesticks
    import datetime
    import pandas
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.resources import CDN

    ticker = 'lpp'
    days_nb = 100

    benchmark = 'WIG20'
    b_df = pandas.read_csv('https://stooq.pl/q/d/l/?s=' + benchmark + '&i=d')
    b_df = b_df[-days_nb:]
    # b_df['Data'] = pandas.to_datetime(b_df['Data'])

    benchmark_index = []
    for d in range(1, days_nb):
        benchmark_val = b_df.iloc[d]['Zamkniecie'] / b_df.iloc[d - 1]['Zamkniecie']
        benchmark_index.append(benchmark_val)


    df = pandas.read_csv('https://stooq.pl/q/d/l/?s=' + ticker + '&i=d')
    df = df[-days_nb:]
    df['Data'] = pandas.to_datetime(df['Data'])

    # start=datetime.datetime(2018,1,1)
    # end=datetime.datetime(2018,11,12)

    def white_black_equal(o, c):
        if c > o:
            v = 'white'
        elif o > c:
            v = 'black'
        else:
            v = 'equal'
        return v

    df['Status'] = [white_black_equal(o, c) for o, c in zip(df.Otwarcie, df.Zamkniecie)]
    df['Middle'] = (df.Otwarcie + df.Zamkniecie) / 2
    df['Height'] = abs(df.Otwarcie - df.Zamkniecie)

    prev_value = df.iloc[0]['Zamkniecie']
    benchmark_list = [prev_value]
    for d in range(days_nb - 1):
        value = prev_value * benchmark_index[d]
        benchmark_list.append(value)
        prev_value = value

    p = figure(x_axis_type='datetime', tools="pan,wheel_zoom,box_zoom,reset", sizing_mode='scale_width')
    p.title.text = ticker
    p.grid.grid_line_alpha = 0.5

    hours_12 = 12 * 60 * 60 * 1000

    p.segment(df.Data, df.Najnizszy, df.Data, df.Najwyzszy, line_color='#737373')

    p.rect(df.Data[df.Status == 'white'], df.Middle[df.Status == 'white'], hours_12,
           df.Height[df.Status == 'white'],
           fill_color='#7FFF00', line_color='#737373')

    p.rect(df.Data[df.Status == 'black'], df.Middle[df.Status == 'black'], hours_12,
           df.Height[df.Status == 'black'],
           fill_color='#ff3333', line_color='#737373')

    p.rect(df.Data[df.Status == 'equal'], df.Middle[df.Status == 'equal'], hours_12,
           df.Height[df.Status == 'equal'],
           fill_color='#ff3333', line_color='#737373')

    p.line(df.Data, benchmark_list, line_color='#B22222')


    script1, div1 = components(p)

    cdn_js=CDN.js_files[0]
    cdn_css=CDN.css_files[0]

    #output_file('chart.html')
    #show(p)

    return render_template('home.html',
                        script1=script1,
                        div1=div1,
                        cdn_css=cdn_css,
                        cdn_js=cdn_js,)

if __name__ == '__main__':
    app.run(debug=True)