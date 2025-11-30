window.addEventListener("load", start, false);

function start()
{
    // custom data range function
    const dataRange = document.getElementById('rangeOptions');
    dataRange.addEventListener('change', function() {
        const dateRange = document.getElementById('dateRange');
        if( this.value === "custom")
        {
            dateRange.innerHTML = '<label for="startDate">Start Date:</label>' +
            '<input type="date" id="startDate"><label for="endDate">End Date:</label>' + 
            '<input type="date" id="endDate">';
        }
        else
            dateRange.innerHTML = '';
    }, false );

    // refresh button function
    const refreshBtn = document.getElementById('refresh');
    refreshBtn.addEventListener('click', () => {
        location.reload();
    }, false);
};

const timeLabels = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'];
const errorLabels = ['R²', 'MAE', 'MSE', 'RMSE', 'EVS'];
const timesLabels = ['10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30'];
const featureLabels = ['mPCB', 'Age', 'Gender', 'BMI', 'Smoking', 'mEducation','Chemical exposure', 'Tea', 'Coffee',
    'Alcohol','Diary', 'Beef/pork', 'Eggs', 'Fish dishes', 'norSalmon','domSalmon', 'Lake Fish','Frozen Fish'];
const PCBsLabels = ['cPCB118', 'cPCB153', 'cPCB138', 'cPCB180',	'cPCB74', 'cPCB99',	'cPCB156', 'cPCB187', 'cPCB183', 'cPCB170'];

// Sample data for charts
const requestData = [45, 59, 80, 81, 56, 55, 40];
// !-- The error metrics reflect real data from our model --!
const errorMetricsData = [0.8067, 0.0896, 0.0167, 0.1293, 0.8703];
const errorRateData = [1.2, 0.8, 0.7, 2.5, 1.0, 0.5, 1.8];
const trainingData = [3.12, 2.98, 2.87, 3.05, 2.91, 2.88, 2.85, 2.92, 2.89, 2.95];
const testingData = [3.45, 3.32, 3.28, 3.35, 3.38, 3.31, 3.25, 3.30, 3.29, 3.33];
// !-- The feature importance reflects real data from our model --!
const featureData = [0.264, 0.99, 0.27, 0.25, 0.70, 0.58, 0.27, 0.32, 0.58, 0.35, 0.03, 0.88,  0.23, 0.92, 0.08, 0.03, 0.41, 0.47];
const PCBsData = [0.1267, 0.4432, 0.7845, 0.2984, 0.5678, 0.8712, 0.3359, 0.6541, 0.9248, 0.2135];

// 1. Request Volume Chart
const requestCtx = document.getElementById('RequestVolume').getContext('2d');
const requestChart = new Chart(requestCtx, {
    // chart type
    type: 'line',
    // data specifications
    data: {
        // x-labels (array)
        labels: timeLabels,
        datasets: [{
            label: 'Request Volume',
            data: requestData,
            backgroundColor: 'rgba(54, 162, 235, 1)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'Hourly Request Volume',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    stepSize: 10,
                    color: 'black'
                },
                title: {
                    display: true,
                    text: 'Number of Requests',
                    color: 'black'
                }
            },
            x : {
                ticks : {
                    color: 'black'
                }
            }
        }
    }
});

// 2. Error Metrics Chart
const MetricsCtx = document.getElementById('ErrorMetrics').getContext('2d');
const MetricsChart = new Chart(MetricsCtx, {
    type: 'bar',
    data: {
        labels: errorLabels,
        datasets: [{
            label: 'Different Metric Types',
            data: errorMetricsData,
            backgroundColor: ['rgba(255, 99, 132, 1)', 'rgb(99, 112, 255, 1)', 'rgb(146, 255, 99, 1)',
                'rgb(99, 255, 255, 1)', 'rgb(255, 148, 99, 1)', 'rgb(0, 38, 208, 1)'],
            borderColor: ['rgba(255, 99, 132, 1)', 'rgb(99, 112, 255, 1)', 'rgb(146, 255, 99, 1)',
                'rgb(99, 255, 255, 1)', 'rgb(255, 148, 99, 1)', 'rgb(0, 38, 208, 1)'],
            borderWidth: 2,
            tension: 0.2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'Different Metric Scores',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    stepSize: 0.5,
                    color: 'black'
                    
                },
                title: {
                    display: true,
                    text: 'Scores',
                    color: 'black'
                }
            },
            x : {
                ticks: {
                    color: 'black'
                }
            }
        }
    }
});

// 3. Error Rates Chart
// should be contructed against days****
const errorCtx = document.getElementById('ErrorRates').getContext('2d');
const errorChart = new Chart(errorCtx, {
    type: 'line',
    data: {
        labels: timeLabels,
        datasets: [{
            label: 'Error Rate (%)',
            data: errorRateData,
            backgroundColor: 'rgba(255, 159, 64, 1)',
            borderColor: 'rgba(255, 159, 64, 1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'Error Rate by Hour',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        },
        scales: {
            y: {
                ticks: {
                    stepSize: 0.25,
                    color: 'black'
                    
                },
                title: {
                    display: true,
                    text: 'Error Rate (%)',
                    color: 'black'
                }
            },
            x : {
                ticks: {
                    color: 'black'
                }
            }
        }
    }
});

// 4. Model Accuracy Chart
const AccuracyCtx = document.getElementById('ModelAccuracy').getContext('2d');
const AccuracyChart = new Chart(AccuracyCtx, {
    type: 'line',
    data: {
        labels: timesLabels,
        datasets: [{
            label: 'Training',
            data: trainingData,
            backgroundColor: 'rgba(0, 132, 188, 1)',
            borderColor: 'rgb(0, 132, 188)',
            borderWidth: 2,
            tension: 0.2
        },
        {
            label: 'Testing',
            data: testingData,
            backgroundColor: 'rgba(40, 202, 0, 1)',
            borderColor: 'rgb(40, 202, 0)',
            borderWidth: 2,
            tension: 0.2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'Training vs Testing',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        },
        scales: {
            y: {
                ticks: {
                    stepSize: 0.1,
                    color: 'black'  
                },
                title: {
                    display: true,
                    text: 'Error Scores',
                    color: 'black'
                }
            },
            x : {
                ticks: {
                    color: 'black'
                }
            }
        }
    }
});

// 5. Feature Importance Chart
const FeatureCtx = document.getElementById('FeaturePlot').getContext('2d');
const FeatureChart = new Chart(FeatureCtx, {
    type: 'pie',
    data: {
        labels: featureLabels,
        datasets: [{
            label: 'Average Response Time (ms)',
            data: featureData,
            backgroundColor: ['rgb(118, 181, 0)', 'rgb(1, 153, 95)', 'rgb(0, 59, 178)', 'rgb(255, 135, 83)', 
                'rgb(255, 251, 3)', 'rgb(153, 1, 80)', 'rgb(102, 13, 110)', 'rgb(255, 70, 70)', 'rgb(200, 123, 50)',
                'rgb(255, 0, 0)', 'rgb(0, 255, 0)', 'rgb(0, 0, 255)', 'rgb(255, 165, 0)', 'rgb(0, 255, 255)',
                'rgb(255, 0, 255)', 'rgb(75, 0, 130)', 'rgb(255, 20, 147)', 'rgb(218, 112, 214)'],
            borderColor: ['rgb(118, 181, 0)', 'rgb(1, 153, 95)', 'rgb(0, 59, 178)', 'rgb(255, 135, 83)', 
                'rgb(255, 251, 3)', 'rgb(153, 1, 80)', 'rgb(102, 13, 110)', 'rgb(255, 70, 70)', 'rgb(200, 123, 50)',
                'rgb(255, 0, 0)', 'rgb(0, 255, 0)', 'rgb(0, 0, 255)', 'rgb(255, 165, 0)', 'rgb(0, 255, 255)',
                'rgb(255, 0, 255)', 'rgb(75, 0, 130)', 'rgb(255, 20, 147)', 'rgb(218, 112, 214)'],
            borderWidth: 2,
            tension: 0.2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'Feature Importance Percentage',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        }
    }
});

// 6. PCBs Importance Plot (Polar Area Chart)
const PCBsCtx = document.getElementById('PCBsPlot').getContext('2d');
const PCBsChart = new Chart(PCBsCtx, {
    type: 'polarArea',
    data: {
        labels: PCBsLabels,
        datasets: [{
            label: 'Average Response Time (ms)',
            data: PCBsData,
            backgroundColor: ['rgb(118, 181, 0)', 'rgb(1, 153, 95)', 'rgb(0, 59, 178)', 'rgb(255, 135, 83)', 'rgb(5, 113, 3)', 
                'rgb(255, 251, 3)', 'rgb(153, 1, 80)', 'rgb(102, 13, 110)', 'rgb(255, 70, 70)', 'rgb(255, 160, 241)'],
            borderColor: ['rgb(118, 181, 0)', 'rgb(1, 153, 95)', 'rgb(0, 59, 178)', 'rgb(255, 135, 83)', 'rgb(5, 113, 3)', 
                'rgb(255, 251, 3)', 'rgb(153, 1, 80)', 'rgb(102, 13, 110)', 'rgb(255, 70, 70)', 'rgb(255, 160, 241)'],
            borderWidth: 2,
            tension: 0.2
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding : {
                top: 10,
                bottom: 20
            }
        },
        plugins: {
            title: {
                display: true,
                text: 'PCBs Importance',
                color: '#ef6a51'
            },
            legend: {
                labels: {
                    color: 'black'
                }
            }
        }
    }
});