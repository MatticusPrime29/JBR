FROM php:8.2-apache

# Install system dependencies (basic utilities only)
RUN apt-get update && apt-get install -y \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Configure Apache
RUN a2enmod rewrite
# Allow .htaccess and fix document root if needed
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf

# Set working directory
WORKDIR /var/www/html

# The application code will be mounted as a volume for development,
# but we set the owner to ensure permissions are correct.
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
