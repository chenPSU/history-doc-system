import {Config} from '@remotion/cli/config';

// Same proven settings as the owner's Lupas project: H.264, CRF 18.
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setCodec('h264');
Config.setCrf(18);
