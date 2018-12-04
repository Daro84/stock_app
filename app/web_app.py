from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

# get data from user - stocks for analysis
@app.route('/analysis/', methods=['POST'])
def analysis():
    global ticker_list
    ticker_list = request.form.getlist('ticker')
    if len(ticker_list) > 0:
        return render_template('analysis.html', ticker_list=ticker_list)
    else:
        return render_template('home.html', text='Please choose at least 1 instrument!')

@app.route('/chart', methods=['POST'])
def chart():
    # import packages to create candlesticks
    import datetime
    import pandas
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.resources import CDN
    # import numpy for satistical analysis
    import numpy as np

    # get data from user - quantity of each stock in portfolio and period of analysis
    if request.method == 'POST':
        quantity_list = request.form.getlist('quantity')
        quantity_list = list(map(int, quantity_list))
        days_nb = int(request.form['days_nb'])

    # trading days in each period
    if days_nb == 21:
        period = 'month'
    elif days_nb == 63:
        period = 'quarter'
    elif days_nb == 250:
        period = 'year'
    elif days_nb == 750:
        period = '3 years'
    elif days_nb == 1250:
        period = '5 years'

    # get data from Stooq.com (csv files) and create dataframe (Date, Open, Close, High, Low) for benchamrk
    benchmark = 'WIG20'
    b_df = pandas.read_csv('https://stooq.pl/q/d/l/?s=' + benchmark + '&i=d')
    b_df = b_df[-days_nb:]
    date_start = b_df.iloc[0]['Data']
    date_end = b_df.iloc[-1]['Data']

    # compute daily returns for benchmark
    benchmark_returns = []
    for d in range(1, days_nb):
        benchmark_ret = b_df.iloc[d]['Zamkniecie'] / b_df.iloc[d - 1]['Zamkniecie']
        benchmark_returns.append(benchmark_ret)

    # create charts and make statistical analysis
    ticker_nb = 0
    charts = []
    data_summary = []

    for t in ticker_list:
        df = pandas.read_csv('https://stooq.pl/q/d/l/?s=' + t + '&i=d')
        df['Data'] = pandas.to_datetime(df['Data'])
        df = df[-days_nb:]
        first_value = df.iloc[0]['Zamkniecie']
        last_value = df.iloc[-1]['Zamkniecie']

        # get data to create relative benchmark line
        bench_value = first_value
        benchmark_chart = [bench_value]
        for d in range(days_nb - 1):
            value = bench_value * benchmark_returns[d]
            benchmark_chart.append(value)
            bench_value = value

        # compute daily returns for each ticker
        ticker_returns = []
        for d in range(1, days_nb):
            ticker_ret = df.iloc[d]['Zamkniecie'] / df.iloc[d - 1]['Zamkniecie']
            ticker_returns.append(ticker_ret)

        # compute rate of return, standard deviation, covariance and beta coefficient
        amount = quantity_list[ticker_nb]
        position_value = round(last_value * amount, 2)
        rate_return = round(100 * ((last_value / first_value) - 1), 2)
        sd = round((np.std(ticker_returns) * 100), 2)
        a = np.array([ticker_returns, benchmark_returns])
        cov = np.cov(a)[0][1]
        benchmark_var = (np.std(benchmark_returns)) ** 2
        beta = round(cov / benchmark_var, 2)

        # create list of dictionaries with data to render chart template
        t_data = dict(ticker=t, last_value=last_value, amount=amount, position_value=position_value,
                      rate_return=rate_return, sd=sd, beta=beta)
        data_summary.append(t_data)

        # add column with status of candle (white body, black body) to dataframe
        def white_black(o, c):
            if c > o:
                v = 'white'
            elif o > c:
                v = 'black'
            else:
                v = 'equal'
            return v

        df['Status'] = [white_black(o, c) for o, c in zip(df.Otwarcie, df.Zamkniecie)]
        df['Middle'] = (df.Otwarcie + df.Zamkniecie) / 2
        df['Height'] = abs(df.Otwarcie - df.Zamkniecie)

        # create bokeh plot
        p = figure(x_axis_type='datetime', width=1200, height=450, title=t + ' - ' + period + ' ' * 10 + date_end,
                   tools="pan,wheel_zoom,box_zoom,reset")
        p.grid.grid_line_alpha = 0.5

        # width of candlestick (in miliseconds)
        hours_18 = 18 * 60 * 60 * 1000

        # height of shadow
        p.segment(df.Data, df.Najnizszy, df.Data, df.Najwyzszy, line_color='#737373')

        # parameters of body
        p.rect(df.Data[df.Status == 'white'], df.Middle[df.Status == 'white'], hours_18,
               df.Height[df.Status == 'white'],
               fill_color='#7FFF00', line_color='#737373')

        p.rect(df.Data[df.Status == 'black'], df.Middle[df.Status == 'black'], hours_18,
               df.Height[df.Status == 'black'],
               fill_color='#ff3333', line_color='#737373')

        p.rect(df.Data[df.Status == 'equal'], df.Middle[df.Status == 'equal'], hours_18,
               df.Height[df.Status == 'equal'] + 0.0001,
               fill_color='#0000FF', line_color='#737373')

        # benchmark line
        p.line(df.Data, benchmark_chart, line_color='#B22222', legend=benchmark + ' - benchmark')

        p.legend.location = "top_left"

        # add chart to list
        charts.append(p)
        ticker_nb += 1

    # embed charts on web page
    script1, div1 = components(charts)
    cdn_js = CDN.js_files[0]
    cdn_css = CDN.css_files[0]

    # compute value of portfolio
    portfolio_value = round(sum([p['position_value'] for p in data_summary]), 2)

    # compute average weighted beta coefficient for portfolio
    position_value_list = [p['position_value'] for p in data_summary]
    beta_list = [b['beta'] for b in data_summary]
    beta_portfolio = round(sum([p * b for p, b in zip(position_value_list, beta_list)]) / portfolio_value, 2)

    return render_template('chart.html',
                           script1=script1,
                           div1=div1,
                           cdn_css=cdn_css,
                           cdn_js=cdn_js,
                           data_summary=data_summary,
                           beta_portfolio=beta_portfolio,
                           portfolio_value=portfolio_value,
                           date_start=date_start,
                           date_end=date_end,
                           period=period)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=False)
