var description_of = {
    "sum":
        "A simple starter example that sums all items in an array.",
    "inner_product":
        "A simple starter example that calculates the dot product of two vectors, this pattern is often observed in linear algebra programs.  This code is taken from <a href='http://www.netlib.org/benchmark/livermorec'>Livermore loops</a>.",
    "tridiag":
        "An example from <a href='http://www.netlib.org/benchmark/livermorec'>Livermore loops</a>, which is a code fragment for solving tri-diagonal linear system of equations.",
    "2mm":
        "A matrix multiplication example taken from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  It computes a matrix <tt>D = alpha * A * B * C + beta * D</tt>, where <tt>A, B, C, D</tt> are 1024x1024 matrices, <tt>alpha, beta</tt> are constant values.",
    "3mm":
        "A matrix-vector multiplication example taken from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  It computes <tt>E = A * B, F = C * D, G = E * F</tt>, where <tt>A, B, C, D, E, F</tt> are 1024x1024 matrices.",
    "atax":
        "A matrix multiplication example taken from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  It computes <tt>y = A * A<sup>T</sup> * x</tt>, where <tt>A</tt> is a 4000x4000 matrix, <tt>A<sup>T</sup></tt> is <tt>A</tt> transposed, and <tt>x, y</tt> are vectors with 4000 elements.",
    "bicg":
        "The <tt>bicg</tt> example from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  BiCG Sub Kernel of BiCGStab Linear Solver.  BiCGStab is an acronym for the <a href='http://mathworld.wolfram.com/BiconjugateGradientStabilizedMethod.html'>biconjugate gradient stabilized method</a>.",
    "gemm":
        "A simple matrix multiplication example taken from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  It computes <tt>C = alpha * A * B + beta * C</tt>, where <tt>A, B, C</tt> are 1024x1024 matrices, <tt>alpha, beta</tt> are contants.",
    "gemver":
        "The <tt>gemver</tt> example from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.",
    "mvt":
        "The <tt>mvt</tt> example from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.  Matrix Vector Product and Transpose.  Our tool identifies that the two nested loops can be fused because they share the same control logic.  This is not yet performed in Vivado HLS 2015.2, and loops are run sequentially even if there are no dependences between them.",
    "seidel":
        "A five point seidel stencil computation, modified from <tt>seidel</tt> in <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.",
    "syr2k":
        "Symmetric Rank-2k Update from <a href='http://web.cs.ucla.edu/~pouchet/software/polybench/'>PolyBench 3.2</a>.",
}

var usage_msg =
    "[Hover over a data-point in one of the graphs below to see the corresponding program.]"

var min_graph_size = 450

var normal_dot_size = 3.5
var original_dot_size = 7
var hover_dot_size = 7

function draw_graph(data, xValue, xdata_label, yValue, ydata_label, graphzone, tooltip, orig_program_textarea, opti_program_textarea) {

  var grossWidth = Math.min(min_graph_size, parseInt(graphzone.style('width'), 10));
  var grossHeight = grossWidth;

  var margin = {top: 20, right: 20, bottom: 100, left: 40},
      width = grossWidth - margin.left - margin.right,
      height = grossHeight - margin.top - margin.bottom;

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
  var svg = graphzone
      .append("svg")
      .attr("width", grossWidth)
      .attr("height", grossHeight)
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
    .attr("r", normal_dot_size)
    .attr("cx", xMap)
    .attr("cy", yMap)
    .attr("eid", function(d) { return d.eid; })
    .style("fill", "black")
    .style("stroke", "black")
    .style("opacity",0.5)
    .on("mouseover", function(d) {
      d3.selectAll(".dot")
    .style("fill", "black")
    .attr("r", normal_dot_size);
      d3.selectAll(".dot[eid='0']")
    .style("fill", "white")
    .attr("r", original_dot_size);;
      d3.selectAll(".dot[eid='"+d.eid+"']")
    .style("fill", "red")
    .attr("r", hover_dot_size);
      opti_program_textarea.text(d.expression);
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
    .attr("r", original_dot_size);

  orig_program_textarea.text(data[0].expression);
  opti_program_textarea.text(usage_msg);

}

var csv_file = "sum";

var run_once = false;
var example_description;
var graphzone1;
var graphzone2;
var graphzone3;
var tooltip;
var orig_program_textarea;
var opti_program_textarea;

function redraw () {

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

    if (!run_once) {
      run_once = true;

      // add the tooltip area to the webpage
      tooltip = d3.select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

      example_description = d3.select("#main_container")
    .append("div")
    .attr("class", "col-md-12")
    .append("p");

      var orig_program = d3.select("#main_container")
      .append("div")
      .attr("class", "col-md-6");

      var opti_program = d3.select("#main_container")
      .append("div")
      .attr("class", "col-md-6");

      orig_program.append("h3").text("Original program");
      orig_program_textarea = orig_program.append("textarea")
    .style("width","100%")
    .attr("rows","20");

      opti_program.append("h3").text("Optimized program");
      opti_program_textarea = opti_program.append("textarea")
    .style("width","100%")
    .attr("rows","20")
    .text(usage_msg);

      graphzone1 = d3.select("#main_container")
    .append("div")
    .attr("class", "col-md-4")

      graphzone2 = d3.select("#main_container")
    .append("div")
    .attr("class", "col-md-4");

      graphzone3 = d3.select("#main_container")
    .append("div")
    .attr("class", "col-md-4");

      graphzone1.append("h3").text("Latency vs. error");
      graphzone2.append("h3").text("LUT count vs. error");
      graphzone3.append("h3").text("LUT count vs. latency");
    }

    example_description.html(description_of[csv_file]);

    var get_error = function(d) {return d.error},
    get_latency = function(d) {return d.latency},
    get_lut = function(d) {return d.lut};

    draw_graph(
        data, get_error, "error", get_latency, "latency (cycles)", graphzone1,
        tooltip, orig_program_textarea, opti_program_textarea);
    draw_graph(
        data, get_error, "error", get_lut, "LUT count", graphzone2,
        tooltip, orig_program_textarea, opti_program_textarea);
    draw_graph(
        data, get_latency, "latency (cycles)", get_lut, "LUT count", graphzone3,
        tooltip, orig_program_textarea, opti_program_textarea);
  });

}

function draw_graphs(new_csv_file) {
  csv_file = new_csv_file;
  redraw ();
}

//window.onresize = redraw;


function init() {
    for (var name in description_of) {
        d3.select('#example_list')
            .append('li')
            .attr('role', 'presentation')
            .attr('id', name)
            .append('a')
            .attr('href', '#select_example')
            .attr('onclick', "draw_graphs('" + name + "')")
            .html(name);
    }
}
init();
