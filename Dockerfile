# Use Apache HTTP Server base image
FROM httpd:2.4-alpine

# Remove default Apache content
RUN rm -rf /usr/local/apache2/htdocs/*

# Copy everything from current directory to Apache htdocs
COPY . /usr/local/apache2/htdocs/

# Expose port 80
EXPOSE 80
