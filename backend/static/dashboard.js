fetch('/api/aggregated_data')
    .then(response => response.json())
    .then(data => {
        const chartsData = [
            { series: 'bdclicks', color: 'rgb(75, 192, 192)', containerId: 'bdclicksChart' },
            { series: 'persons', color: 'rgb(255, 99, 132)', containerId: 'personsChart' },
            { series: 'payments', color: 'rgb(54, 162, 235)', containerId: 'paymentsChart' },
            { series: 'packs', color: 'rgb(255, 206, 86)', containerId: 'packsChart' },
        ];

        const margin = { top: 20, right: 20, bottom: 30, left: 40 };
        const width = 600 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;

        // Define the zoomed function
        function zoomed(event) {
            const { transform } = event;

            // Get the updated x-scale based on the zoom transform
            const xScale = transform.rescaleX(x);

            // Update the x-axis for each chart
            svg.select(".x-axis").call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%Y-%m-%d")));

            // Update the bars' position and width based on the updated x-scale
            svg.selectAll(".bar")
                .attr("x", d => xScale(d.hour))
                .attr("width", xScale.bandwidth());
        }

        // Create a shared zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([1, 8])
            .extent([[0, 0], [width, height]])
            .translateExtent([[0, 0], [width, height]])
            .on("zoom", zoomed);

        chartsData.forEach(chartData => {
            const { series, color, containerId } = chartData;

            const hourlyData = data[`${series}`];
            const dailyData = Array.from(d3.rollup(hourlyData, v => d3.sum(v, d => d.value), d => d.hour.substring(0, 10)), ([hour, value]) => ({ hour, value }));

            const x = d3.scaleBand()
                .range([0, width])
                .padding(0.1)
                .domain(dailyData.map(d => d.hour));

            const y = d3.scaleLinear()
                .range([height, 0])
                .domain([0, d3.max(dailyData, d => d.value)]);

            const svg = d3.select(`#${containerId}`)
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
                .call(zoom); // Apply the zoom behavior to the SVG

            svg.selectAll(".bar")
                .data(dailyData)
                .enter()
                .append("rect")
                .attr("class", "bar")
                .attr("x", d => x(d.hour))
                .attr("y", d => y(d.value))
                .attr("width", x.bandwidth())
                .attr("height", d => height - y(d.value))
                .attr("fill", color);

            svg.append("g")
                .attr("class", "x-axis")
                .attr("transform", "translate(0," + height + ")")
                .call(d3.axisBottom(x).tickFormat(d3.timeFormat("%Y-%m-%d")))
                .selectAll("text")
                .attr("transform", "rotate(-45)")
                .attr("text-anchor", "end");

            svg.append("g")
                .attr("class", "y-axis")
                .call(d3.axisLeft(y));

            svg.append("text")
                .attr("class", "chart-label")
                .attr("x", width / 2)
                .attr("y", -10)
                .text(series);

        });
    })
    .catch(error => console.error('Error:', error));
