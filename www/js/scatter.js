var margin = {top: 20, right: 20, bottom: 100, left: 40},
    width = 300 - margin.left - margin.right,
    height = 300 - margin.top - margin.bottom;

var usage_msg =
    "[Hover over a data-point in one of the graphs to see the corresponding program.]"



function draw_graph(data, xValue, xdata_label, yValue, ydata_label, graphzone,tooltip) {

  /* 
   * value - returns the value to encode for a given data object.
   * scale - maps value to a visual display encoding, such as a pixel position.
   * map   - maps from data value to display value
   * axis  - sets up axis
   */ 
  
  // setup x 
  var xScale = d3.scale.linear().range([0, width]), // value -> display
      xMap = function(d) { return xScale(xValue(d));}, // data -> display
      xAxis = d3.svg.axis().scale(xScale).orient("bottom");
  
  // setup y
  var yScale = d3.scale.linear().range([height, 0]), // value -> display
      yMap = function(d) { return yScale(yValue(d));}, // data -> display
      yAxis = d3.svg.axis().scale(yScale).orient("left");

  var axisformatter = d3.format(".3s");
  
  // add the graph canvas to the body of the webpage
  var svg = d3.select("#"+graphzone)
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
 
  
  // don't want dots overlapping axis, so add in buffer to data domain
  xScale.domain([d3.min(data, xValue), d3.max(data, xValue)]);
  yScale.domain([d3.min(data, yValue), d3.max(data, yValue)]);
  
  // x-axis
  var xaxis = svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis 
	    .tickFormat(function(d) { return axisformatter(d) }));      
  
  xaxis.selectAll("text")	
    .style("text-anchor", "end")
    .attr("dx", "-.8em")
    .attr("dy", ".15em")
    .attr("transform", function(d) {
      return "rotate(-65)" 
    });
  
  xaxis.append("text")
    .attr("class", "label")
    .attr("x", width)
    .attr("y", -6)
    .style("text-anchor", "end")
    .text(xdata_label);
  
  // y-axis
  var yaxis = svg.append("g")
      .attr("class", "y axis")
      .call(yAxis
	    .tickFormat(function(d) { return axisformatter(d) }));
  
  yaxis.append("text")
    .attr("class", "label")
    .attr("transform", "rotate(-90)")
    .attr("y", 6)
    .attr("dy", ".71em")
    .style("text-anchor", "end")
    .text(ydata_label);
  
  // draw dots
  svg.selectAll(".dot")
    .data(data)
    .enter()
    .append("circle")
    .attr("class", "dot")
    .attr("r", 3.5)
    .attr("cx", xMap)
    .attr("cy", yMap)
    .attr("eid", function(d) { return d.eid; })
    .style("fill", "black")
    .style("stroke", "black")
    .style("opacity",0.5)
    .on("mouseover", function(d) {
      d3.selectAll(".dot")
	.style("fill","black")
	.attr("r", 3.5);
      d3.selectAll(".dot[eid='0']")
	.style("fill","white")
	.attr("r", 5);;
      d3.selectAll(".dot[eid='"+d.eid+"']")
	.style("fill","red")
	.attr("r", 5);
      d3.select('#opti_program')
	.text(d.expression);
      tooltip.transition()
        .duration(200)
        .style("opacity", .9);
      tooltip.html(xdata_label + ": " + axisformatter(xValue(d)) + "<br />" +
		   ydata_label + ": " + axisformatter(yValue(d)))
        .style("left", (d3.event.pageX + 5) + "px")
        .style("top", (d3.event.pageY - 28) + "px");
    })
    .on("mouseout", function(d) {
      tooltip.transition()
        .duration(500)
        .style("opacity", 0);
    });
  

  d3.selectAll(".dot[eid='0']")
    .style("fill","white")
    .attr("r", 5);
  
  d3.select('#orig_program')
    .text(data[0].expression);
  
}

function draw_graphs(csv_file) {
 
  csv_file = csv_file.value;
  
  // load data
  d3.csv("csv/" + csv_file + ".csv", function(_, data) {
    
    // change string (from CSV) into number format
    data.forEach(function(d) {
      d.error = +d.error;
      d.latency = +d.latency;
      d.lut = +d.lut;
    });
    
    // add primary key for each row
    var ctr = 0;
    data.forEach(function(d) {
      d.eid = ctr;
      ctr++;
    });
   
    // Remove any previous graphs
    d3.selectAll("svg").remove();
    d3.select('#opti_program').text(usage_msg);

    // add the tooltip area to the webpage
    var tooltip = d3.select("body").append("div")
	.attr("class", "tooltip")
	.style("opacity", 0);
    
    var get_error = function(d) {return d.error},
	get_latency = function(d) {return d.latency},
	get_lut = function(d) {return d.lut};
    
    draw_graph(data, get_error, "error", get_latency, "latency", "graphzone1",tooltip);
    draw_graph(data, get_error, "error", get_lut, "lut", "graphzone2",tooltip);
    draw_graph(data, get_latency, "latency", get_lut, "lut", "graphzone3",tooltip);
    
  });
  
}
