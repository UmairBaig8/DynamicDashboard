import streamlit as st
import streamlit.components.v1 as components

# Define your HTML and JavaScript
html = """
    <table id="myTable">
        <thead>
            <tr>
                <th>header1</th>
                <th>header2</th>
                <th>header3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>text1.1</td>
                <td>text1.2</td>
                <td>text1.3</td>
            </tr>
            <tr>
                <td>text2.1</td>
                <td>text2.2</td>
                <td>text2.3</td>
            </tr>
            <tr>
                <td>text3.1</td>
                <td>text3.2</td>
                <td>text3.3</td>
            </tr>
        </tbody>
    </table>
    <button onclick="addRow()">Add Row</button>
    <script>
        function addRow() {
            var table = document.getElementById("myTable").getElementsByTagName('tbody')[0];
            var newRow = table.insertRow();
            var cell1 = newRow.insertCell(0);
            var cell2 = newRow.insertCell(1);
            var cell3 = newRow.insertCell(2);
            cell1.innerHTML = "new text1";
            cell2.innerHTML = "new text2";
            cell3.innerHTML = "new text3";
        }
    </script>
"""

# Use the components API to render the HTML
components.html(html, height=300)