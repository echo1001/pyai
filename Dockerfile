# FROM nvcr.io/nvidia/deepstream-l4t:5.0.1-20.09-samples
FROM nvcr.io/nvidia/deepstream-l4t:5.1-21.02-samples

# apt-get install -y software-properties-common
# add-apt-repository -y ppa:pypy/ppa
# apt-get update
# apt-get install -y pypy3

# apt-get install wget libjpeg9 libjpeg9-dev

RUN apt-get update && apt-get install -y \
  python3.6 \
  python3-wheel \
  python3-setuptools \
  python3-pip \
  python3-pil \
  python3-numpy \
  libcairo2 \
  libcairo2-dev \ 
  libgeos-dev \
  libgstreamer1.0-0 \
  libgstreamer1.0-dev \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
  libgstreamer-plugins-base1.0-dev \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0 \ 
  python-gobject-2-dev libgirepository1.0-dev python3-cairo-dev && pip3 install --upgrade pip 

COPY . /opt/pyai
RUN cd /opt/pyai && pip3 install --editable .
RUN cd /opt/pyai && cp libnvdsgst_infer.so /opt/nvidia/deepstream/deepstream/lib/gst-plugins
  
  # && \
  #cd /opt/nvidia/deepstream/deepstream-5.1/sources/gst-plugins/gst-nvinfer && CUDA_VER=10.2 make && make install
WORKDIR /opt/config
CMD pyai