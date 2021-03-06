/*
  Firmware for second generation reader (Bell series).

  ADS gain settings (must convert for 3.3V):
                                                                ADS1015  ADS1115
                                                                -------  -------
  ads.setGain(GAIN_TWOTHIRDS);  // 2/3x gain +/- 6.144V  1 bit = 3mV      0.1875mV (default)
  ads.setGain(GAIN_ONE);        // 1x gain   +/- 4.096V  1 bit = 2mV      0.125mV
  ads.setGain(GAIN_TWO);        // 2x gain   +/- 2.048V  1 bit = 1mV      0.0625mV
  ads.setGain(GAIN_FOUR);       // 4x gain   +/- 1.024V  1 bit = 0.5mV    0.03125mV
  ads.setGain(GAIN_EIGHT);      // 8x gain   +/- 0.512V  1 bit = 0.25mV   0.015625mV
  ads.setGain(GAIN_SIXTEEN);    // 16x gain  +/- 0.256V  1 bit = 0.125mV  0.0078125mV
*/

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_ADS1015.h>

Adafruit_ADS1115 ads1115(0x48); // Instantiate ADS1115

// const float multiplier = 0.1875e-3F; // GAIN_TWOTHIRDS
const float multiplier = 0.125e-3F; // GAIN_ONE
// const float multiplier = 0.0625e-3F; // GAIN_TWO
// const float multiplier = 0.03125e-3F; // GAIN_FOUR
// const float multiplier = 0.015625e-3F; // GAIN_EIGHT
// const float multiplier = 0.0078125e-3F; // GAIN_SIXTEEN

const float rRef = 10e3; // Reference resistor in current follower

// User input for setup
String readerSetting;
int medianUser;
int amplitudeUser;
int frequencyUser;
float periodUser;

// DAC and gating parameters
uint16_t dacRes = 4096;      // Resolution (minimum step size) of 12 bit DAC
uint16_t indexGround = 2048; // Ground potential index
uint16_t indexConstPot;      // Constant potential index
uint16_t indexTopLim;        // Gate top limit index (positive voltage input)
uint16_t indexBtmLim;        // Gate bottom limit index (negative voltage input)
uint16_t stepSize;           // Step size for gate sweep

// Variables for computing DAC index along waveform
int phase1;
int phase2;
int phase3;
int phase4;

const int chipSelectPin = 2; // DAC chip select pin

float readADC()
{
  int16_t adc = ads1115.readADC_SingleEnded(0); // Read ADC Channel 0
  float v = (float)adc * multiplier;            // Calculate voltage using multiplier
  return v / rRef * 1.0e6;                      // Convert signal to current based on output voltage and reference resistor
}

void writeDAC(uint16_t data, uint8_t chipSelectPin)
{
  // Take top 4 bits of config and top 4 valid bits (data is actually a 12 bit number) and OR them together
  uint8_t config = 0x30;
  uint8_t topMsg = (config & 0xF0) | (0x0F & (data >> 8));

  uint8_t lowerMsg = (data & 0x00FF); // Take the bottom octet of data

  digitalWrite(chipSelectPin, LOW); // Select DAC, active LOW

  SPI.transfer(topMsg);   // Send first 8 bits
  SPI.transfer(lowerMsg); // Send second 8 bits

  digitalWrite(chipSelectPin, HIGH); // Deselect DAC
}

void setupDAC()
{
  float vRefDAC = (float)analogRead(A0) * (3300.0 / 1023.0); // Determine value of vRef for the DAC
  float maxRange = 2.0 * vRefDAC;                            // Full range of gate sweep (mV)
  float smallStep = maxRange / (float)dacRes;                // Voltage increment based on DAC resolution

  // Serial.print("vRefDAC: ");
  // Serial.println(vRefDAC);
  // Serial.print("smallStep: ");
  // Serial.println(smallStep);

  // Setup for constant non-zero potential setting
  if (readerSetting == "c")
  {
    indexConstPot = indexGround + (int)((float)medianUser / smallStep); // Even though smallStep is a float, value becomes an int

    // Serial.print("indexConstPot: ");
    // Serial.println(indexConstPot);
  }

  // Setup for sweep and transfer curve settings
  else if (readerSetting == "s")
  {
    indexTopLim = indexGround + (int)(((float)medianUser + (float)amplitudeUser) / smallStep);
    indexBtmLim = indexGround + (int)((float)medianUser - (float)amplitudeUser / smallStep);

    phase1 = indexTopLim - indexGround;
    phase2 = indexGround - indexTopLim;
    phase3 = indexBtmLim - indexGround;
    phase4 = indexGround - indexBtmLim;

    periodUser = 1.0e6 / (float)frequencyUser; // Period in milliseconds

    // Serial.print("Index top limit: ");
    // Serial.println(indexTopLim);
    // Serial.print("Index bottom limit: ");
    // Serial.println(indexBtmLim);

    // Serial.print("Phase1: ");
    // Serial.println(phase1);
    // Serial.print("Phase2: ");
    // Serial.println(phase2);
    // Serial.print("Phase3: ");
    // Serial.println(phase3);
    // Serial.print("Phase4: ");
    // Serial.println(phase4);
    // Serial.print("Period: ");
    // Serial.println(periodUser, 6);
  }
}

uint16_t sweepIndex(unsigned long timeExperiment)
{
  uint16_t indexDAC;
  float interval = fmod(timeExperiment, periodUser) / periodUser; // Find point in waveform
  // Serial.print("Interval: ");
  // Serial.println(interval, 5);

  // Map interval to corresponding index
  if (interval <= 0.25)
  {
    indexDAC = (uint16_t)round((float)indexGround + (interval / 0.25 * phase1));
  }
  else if ((interval > 0.25) && (interval <= 0.5))
  {
    indexDAC = (uint16_t)round((float)indexGround + ((interval - 0.5) / 0.25 * phase2));
  }
  else if ((interval > 0.5) && (interval <= 0.75))
  {
    indexDAC = (uint16_t)round((float)indexGround + ((interval - 0.5) / 0.25 * phase3));
  }
  else
  {
    indexDAC = (uint16_t)round((float)indexGround + ((interval - 1.0) / 0.25 * phase4));
  }

  // Serial.print("DAC index: ");
  // Serial.println(indexDAC);

  return indexDAC;
}

void serialReadSetup()
{
  String dataStr = "";    // Variable that stores entire data transmission
  char dataChar;          // Individual data character read from buffer
  char startMarker = '<'; // Indicates beginning of message
  char endMarker = '>';   // Indicates end of message
  char resetMarker = 'e'; // Reset system
  static boolean receiveInProgress = false;

  // While data in serial buffer...
  while (Serial.available() > 0)
  {
    // Read individual character from stream, in sequence
    dataChar = Serial.read();

    if (receiveInProgress == true)
    {
      if (dataChar != endMarker)
      {
        dataStr += dataChar;
      }
      else
      {
        receiveInProgress = false;
      }
    }
    else if (dataChar == startMarker)
    {
      receiveInProgress = true;
    }
    else if (dataChar == resetMarker)
    {
      NVIC_SystemReset(); // Processor software reset
    }
  }

  // Extract data from transmission
  int firstDelim = dataStr.indexOf(';');
  readerSetting = dataStr.substring(0, firstDelim);

  int secondDelim = dataStr.indexOf(';', firstDelim + 1);
  String medianInput = dataStr.substring(firstDelim + 1, secondDelim);
  medianUser = medianInput.toInt();

  int thirdDelim = dataStr.indexOf(';', secondDelim + 1);
  String amplitudeInput = dataStr.substring(secondDelim + 1, thirdDelim);
  amplitudeUser = amplitudeInput.toInt();

  String frequencyInput = dataStr.substring(thirdDelim + 1, -1);
  frequencyUser = frequencyInput.toInt();

  // Serial.print("Setting: ");
  // Serial.println(readerSetting);
  // Serial.print("Median: ");
  // Serial.println(medianUser);
  // Serial.print("Amplitude: ");
  // Serial.println(amplitudeUser);
  // Serial.print("Frequency: ");
  // Serial.println(frequencyUser);
}

void serialTransmission(unsigned long timeExperiment, float iSen)
{
  Serial.print(timeExperiment);
  Serial.print(',');
  Serial.println(iSen, 3);
}

void setup()
{
  // Initialize ADS1115 and set amplifier gain
  ads1115.begin();
  ads1115.setGain(GAIN_ONE);

  // Initialize SPI communication (DAC)
  SPI.begin();
  SPI.setClockDivider(SPI_CLOCK_DIV8);

  pinMode(chipSelectPin, OUTPUT);
  digitalWrite(chipSelectPin, HIGH);    // Initialize CS pin in default state
  writeDAC(indexGround, chipSelectPin); // Immediately set to ground potential

  Serial.begin(500000); // Set baud rate for serial communication
  // delay(100);

  while (Serial.available() < 1)
  {
    ; // Delay until incoming message from user
  }
}

void loop()
{
  unsigned long timeStart, timeExperiment;
  float iSen;
  uint16_t indexDAC;

  serialReadSetup();
  setupDAC();

  {
    // Option 1: hold counter electrode at steady potential
    if (readerSetting == "c")
    {
      writeDAC(indexConstPot, chipSelectPin);
      timeStart = millis();
      while (Serial.available() < 1)
      {
        timeExperiment = millis() - timeStart;
        iSen = readADC();
        serialTransmission(timeExperiment, iSen);
      }
    }

    // Option 2: sweep counter electrode
    else if (readerSetting == "s")
    {
      timeStart = millis();
      while (Serial.available() < 1)
      {
        timeExperiment = millis() - timeStart;
        indexDAC = sweepIndex(timeExperiment);
        writeDAC(indexDAC, chipSelectPin);
        iSen = readADC();
        serialTransmission(timeExperiment, iSen);
      }
    }
  }
}